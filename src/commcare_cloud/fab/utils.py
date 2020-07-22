from __future__ import absolute_import
from __future__ import print_function
import datetime
import os
import pickle
import sys
import traceback
from fabric.operations import sudo
from fabric.context_managers import cd, settings
from fabric.api import local
import re
from getpass import getpass
from memoized import memoized_property, memoized

from github import Github, UnknownObjectException
from fabric.api import execute, env
from fabric.colors import magenta, red
from gevent.pool import Pool
from collections import defaultdict

from .const import (
    PROJECT_ROOT,
    CACHED_DEPLOY_CHECKPOINT_FILENAME,
    CACHED_DEPLOY_ENV_FILENAME,
    DATE_FMT,
    OFFLINE_STAGING_DIR,
    RELEASE_RECORD,
)

from six.moves import input

LABELS_TO_EXPAND = [
    "reindex/migration",
]


def execute_with_timing(fn, *args, **kwargs):
    start_time = datetime.datetime.utcnow()
    execute(fn, *args, **kwargs)
    if env.timing_log:
        with open(env.timing_log, 'a') as timing_log:
            duration = datetime.datetime.utcnow() - start_time
            timing_log.write('{}: {}\n'.format(fn.__name__, duration.seconds))


def get_pillow_env_config():
    full_host = env.get('host_string')
    if full_host and '.' in full_host:
        host = full_host.split('.')[0]

    pillows = {}
    pillows.update(env.pillows.get(host, {}))
    pillows.update(env.pillows.get(full_host, {}))
    return pillows


class DeployMetadata(object):

    def __init__(self, code_branch, environment):
        self.timestamp = datetime.datetime.utcnow().strftime(DATE_FMT)
        self._deploy_tag = None
        self._max_tags = 100
        self._code_branch = code_branch
        self._environment = environment

    @memoized_property
    def repo(self):
        return _get_github().get_repo('dimagi/commcare-hq')

    @memoized_property
    def last_commit_sha(self):
        with cd(env.code_current):
            return sudo('git rev-parse HEAD')

    def tag_commit(self):
        if env.offline:
            self._offline_tag_commit()
            return

        tag_name = "{}-{}-deploy".format(self.timestamp, self._environment)
        if _github_auth_provided():
            self.repo.create_git_ref(
                ref='refs/tags/' + tag_name,
                sha=self.deploy_ref,
            )
            self._deploy_tag = tag_name

    def _offline_tag_commit(self):
        commit = local('cd {}/commcare-hq && git show-ref --hash --heads {}'.format(
            OFFLINE_STAGING_DIR,
            env.deploy_metadata.deploy_ref,
        ), capture=True)

        tag_name = '{}-{}-offline-deploy'.format(
            self.timestamp, self._environment)
        local('cd {staging_dir}/commcare-hq && git tag -a -m "{message}" {tag} {commit}'.format(
            staging_dir=OFFLINE_STAGING_DIR,
            message='{} offline deploy at {}'.format(
                self._environment, self.timestamp),
            tag=tag_name,
            commit=commit,
        ))

        with settings(warn_only=True):
            local('cd {staging_dir}/commcare-hq && git push origin {tag}'.format(
                staging_dir=OFFLINE_STAGING_DIR,
                tag=tag_name,
            ))

    @memoized_property
    def deploy_ref(self):
        if env.offline:
            return env.code_branch

        # turn whatever `code_branch` is into a commit hash
        return self.repo.get_commit(self._code_branch).sha

    def tag_setup_release(self):
        if _github_auth_provided():
            try:
                self.repo.create_git_ref(
                    ref='refs/tags/' +
                        '{}-{}-setup_release'.format(self.timestamp,
                                                     self._environment),
                    sha=self.deploy_ref,
                )
            except UnknownObjectException:
                raise Exception(
                    'Github API key does not have the right settings. '
                    'Please create an API key with the public_repo scope enabled.'
                )
            return True
        return False

    @property
    def current_ref_is_different_than_last(self):
        return self.deploy_ref != self.last_commit_sha

    @memoized_property
    def diff(self):
        return DeployDiff(self.repo, self.last_commit_sha, self.deploy_ref)


@memoized
def _get_github_credentials():
    try:
        from .config import GITHUB_APIKEY
    except ImportError:
        print(red("Github credentials not found!"))
        print("This deploy script uses the Github API to display a summary of changes to be deployed.")
        if env.tag_deploy_commits:
            print("You're deploying an environment which uses release tags. "
                  "Provide Github auth details to enable release tags.")
        print((
            "You can add a config file to automate this step:\n"
            "    $ cp {project_root}/config.example.py {project_root}/config.py\n"
            "Then edit {project_root}/config.py"
        ).format(project_root=PROJECT_ROOT))
        username = input('Github username (leave blank to skip): ') or None
        password = getpass('Github password: ') if username else None
        return (username, password)
    else:
        return (GITHUB_APIKEY, None)


@memoized
def _get_github():
    login_or_token, password = _get_github_credentials()
    return Github(login_or_token=login_or_token, password=password)


@memoized
def _github_auth_provided():
    return bool(_get_github_credentials()[0])


def _get_checkpoint_filename():
    return '{}_{}'.format(env.deploy_env, CACHED_DEPLOY_CHECKPOINT_FILENAME)


def _get_env_filename():
    return '{}_{}'.format(env.deploy_env, CACHED_DEPLOY_ENV_FILENAME)


def cache_deploy_state(command_index):
    with open(os.path.join(PROJECT_ROOT, _get_checkpoint_filename()), 'w') as f:
        pickle.dump(command_index, f)
    with open(os.path.join(PROJECT_ROOT, _get_env_filename()), 'w') as f:
        pickle.dump(env, f)


def clear_cached_deploy():
    os.remove(os.path.join(PROJECT_ROOT, _get_checkpoint_filename()))
    os.remove(os.path.join(PROJECT_ROOT, _get_env_filename()))


def retrieve_cached_deploy_env():
    filename = os.path.join(PROJECT_ROOT, _get_env_filename())
    return _retrieve_cached(filename)


def retrieve_cached_deploy_checkpoint():
    filename = os.path.join(PROJECT_ROOT, _get_checkpoint_filename())
    return _retrieve_cached(filename)


def _retrieve_cached(filename):
    with open(filename, 'r') as f:
        return pickle.load(f)


def traceback_string():
    exc_type, exc, tb = sys.exc_info()
    trace = "".join(traceback.format_tb(tb))
    return u"Traceback:\n{trace}{type}: {exc}".format(
        trace=trace,
        type=exc_type.__name__,
        exc=exc,
    )


def pip_install(cmd_prefix, requirements, timeout=None, quiet=False, proxy=None, no_index=False,
                wheel_dir=None):
    parts = [cmd_prefix, 'pip install']
    if timeout is not None:
        parts.append('--timeout {}'.format(timeout))
    if quiet:
        parts.append('--quiet')
    for requirement in requirements:
        parts.append('--requirement {}'.format(requirement))
    if proxy is not None:
        parts.append('--proxy {}'.format(proxy))
    if no_index:
        parts.append('--no-index')
    if wheel_dir is not None:
        parts.append('--find-links={}'.format(wheel_dir))
    sudo(' '.join(parts))


def generate_bower_command(command, production=True, config=None):
    parts = ['bower', command]
    if production:
        parts.append('--production')
    if config:
        for key, value in config.items():
            parts.append('--config.{}={}'.format(key, value))
    return ' '.join(parts)


def bower_command(command, production=True, config=None):
    cmd = generate_bower_command(command, production, config)
    sudo(cmd)


class DeployDiff:
    def __init__(self, repo, last_commit, deploy_commit):
        self.repo = repo
        self.last_commit = last_commit
        self.deploy_commit = deploy_commit

    @property
    def url(self):
        """Human-readable diff URL"""
        return "{}/compare/{}...{}".format(self.repo.html_url, self.last_commit, self.deploy_commit)

    def warn_of_migrations(self):
        if not _github_auth_provided():
            return

        pr_numbers = self._get_pr_numbers()
        pool = Pool(5)
        pr_infos = [_f for _f in pool.map(self._get_pr_info, pr_numbers) if _f]

        print("List of PRs since last deploy:")
        self._print_prs_formatted(pr_infos)

        prs_by_label = self._get_prs_by_label(pr_infos)
        if prs_by_label:
            print(red('You are about to deploy the following PR(s), which will trigger a reindex or migration. Click the URL for additional context.'))
            self._print_prs_formatted(prs_by_label['reindex/migration'])

    def _get_pr_numbers(self):
        comparison = self.repo.compare(self.last_commit, self.deploy_commit)
        return [
            int(re.search(r'Merge pull request #(\d+)',
                          repo_commit.commit.message).group(1))
            for repo_commit in comparison.commits
            if repo_commit.commit.message.startswith('Merge pull request')
        ]

    def _get_pr_info(self, pr_number):
        pr_response = self.repo.get_pull(pr_number)
        if not pr_response.number:
            # Likely rate limited by Github API
            return None
        assert pr_number == pr_response.number, (pr_number, pr_response.number)

        labels = [label.name for label in pr_response.labels]

        return {
            'title': pr_response.title,
            'url': pr_response.html_url,
            'labels': labels,
        }

    def _get_prs_by_label(self, pr_infos):
        prs_by_label = defaultdict(list)
        for pr in pr_infos:
            for label in pr['labels']:
                if label in LABELS_TO_EXPAND:
                    prs_by_label[label].append(pr)
        return dict(prs_by_label)

    def _print_prs_formatted(self, pr_list):
        i = 1
        for pr in pr_list:
            print("{0}. ".format(i), end="")
            print("{title} {url} | ".format(**pr), end="")
            print(" ".join(label for label in pr['labels']))
            i += 1

