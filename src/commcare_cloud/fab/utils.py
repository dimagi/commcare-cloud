from __future__ import absolute_import, print_function, unicode_literals

import datetime
import os
import pickle
import sys
import traceback
from io import open

from fabric.api import env, execute, local
from fabric.context_managers import cd, settings
from fabric.operations import sudo
from github import UnknownObjectException
from memoized import memoized_property

from .const import (
    CACHED_DEPLOY_CHECKPOINT_FILENAME,
    CACHED_DEPLOY_ENV_FILENAME,
    DATE_FMT,
    OFFLINE_STAGING_DIR,
    PROJECT_ROOT,
)
from .deploy_diff import DeployDiff
from .git_repo import get_github, github_auth_provided


def execute_with_timing(fn, *args, **kwargs):
    start_time = datetime.datetime.utcnow()
    execute(fn, *args, **kwargs)
    if env.timing_log:
        with open(env.timing_log, 'a', encoding='utf-8') as timing_log:
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
        self.timestamp = environment.new_release_name
        self._deploy_tag = None
        self._max_tags = 100
        self._code_branch = code_branch
        self._environment = environment
        self._deploy_env = environment.meta_config.deploy_env

    def __getstate__(self):
        """
        HACK: Remove memoized property values to allow object to be pickled
        Removes any attribute that begins with '_' and ends with '_cache'
        which is the naming scheme for memoized properties
        """
        state = dict(self.__dict__)
        for key in list(state):
            if key.startswith('_') and key.endswith('_cache'):
                del state[key]

        return state

    @memoized_property
    def repo(self):
        return get_github().get_repo('dimagi/commcare-hq')

    @memoized_property
    def last_commit_sha(self):
        with cd(env.code_current):
            return sudo('git rev-parse HEAD')

    def tag_commit(self):
        if env.offline:
            self._offline_tag_commit()
            return

        tag_name = "{}-{}-deploy".format(self.timestamp, self._deploy_env)
        if github_auth_provided():
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
            self.timestamp, self._deploy_env)
        local('cd {staging_dir}/commcare-hq && git tag -a -m "{message}" {tag} {commit}'.format(
            staging_dir=OFFLINE_STAGING_DIR,
            message='{} offline deploy at {}'.format(
                self._deploy_env, self.timestamp),
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
        if github_auth_provided():
            try:
                self.repo.create_git_ref(
                    ref='refs/tags/' +
                        '{}-{}-setup_release'.format(self.timestamp,
                                                     self._deploy_env),
                    sha=self.deploy_ref,
                )
            except UnknownObjectException:
                raise Exception(
                    'Github API key does not have the right settings. '
                    'Please create an API key with the public_repo scope enabled.'
                )
            return True
        return False

    @memoized_property
    def diff(self):
        return DeployDiff(self.repo, self.last_commit_sha, self.deploy_ref)


def _get_checkpoint_filename():
    return '{}_{}'.format(env.deploy_env, CACHED_DEPLOY_CHECKPOINT_FILENAME)


def _get_env_filename():
    return '{}_{}'.format(env.deploy_env, CACHED_DEPLOY_ENV_FILENAME)


def cache_deploy_state(command_index):
    with open(os.path.join(PROJECT_ROOT, _get_checkpoint_filename()), 'wb') as f:
        pickle.dump(command_index, f)
    with open(os.path.join(PROJECT_ROOT, _get_env_filename()), 'wb') as f:
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
    with open(filename, 'rb') as f:
        return pickle.load(f)


def traceback_string():
    exc_type, exc, tb = sys.exc_info()
    trace = "".join(traceback.format_tb(tb))
    return "Traceback:\n{trace}{type}: {exc}".format(
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
