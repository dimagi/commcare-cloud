import datetime
import os
import yaml
import re
from getpass import getpass

from github3 import login
from fabric.api import execute, env
from fabric.colors import magenta

from .const import PROJECT_ROOT

from const import PROJECT_ROOT


def execute_with_timing(fn, *args, **kwargs):
    start_time = datetime.datetime.utcnow()
    execute(fn, *args, **kwargs)
    if env.timing_log:
        with open(env.timing_log, 'a') as timing_log:
            duration = datetime.datetime.utcnow() - start_time
            timing_log.write('{}: {}\n'.format(fn.__name__, duration.seconds))


def get_pillow_env_config(environment):
    pillow_conf = {}
    pillow_file = os.path.join(PROJECT_ROOT, 'pillows', '{}.yml'.format(environment))
    if os.path.exists(pillow_file):
        with open(pillow_file, 'r+') as f:
            yml = yaml.load(f)
            pillow_conf.update(yml)
    else:
        return None

    return pillow_conf


class DeployMetadata(object):
    def __init__(self, code_branch, environment):
        self.timestamp = datetime.datetime.utcnow().strftime('%Y-%m-%d_%H.%M')
        self._deploy_ref = None
        self._deploy_tag = None
        self._github = _get_github()
        self._repo = self._github.repository('dimagi', 'commcare-hq')
        self._max_tags = 100
        self._last_tag = None
        self._code_branch = code_branch
        self._environment = environment

    def tag_commit(self):
        pattern = ".*-{}-.*".format(re.escape(self._environment))
        for tag in self._repo.tags(self._max_tags):
            if re.match(pattern, tag.name):
                self._last_tag = tag.name
                break

        if not self._last_tag:
            print magenta('Warning: No previous tag found in last {} tags for {}'.format(
                self._max_tags,
                self._environment
            ))
        tag_name = "{}-{}-deploy".format(self.timestamp, self._environment)
        msg = "{} deploy at {}".format(self._environment, self.timestamp)
        user = self._github.me()
        self._repo.create_tag(
            tag=tag_name,
            message=msg,
            sha=self.deploy_ref,
            obj_type='commit',
            tagger={
                'name': user.login,
                'email': user.email or '{}@dimagi.com'.format(user.login),
                'date': datetime.datetime.utcnow().strftime('%Y-%m-%dT%H:%M:%SZ'),
            }
        )
        self._deploy_tag = tag_name

    @property
    def diff_url(self):
        if self._deploy_tag is None:
            raise Exception("You haven't tagged anything yet.")
        return "https://github.com/dimagi/commcare-hq/compare/{}...{}".format(
            self._last_tag,
            self._deploy_tag,
        )

    @property
    def deploy_ref(self):
        if self._deploy_ref is None:
            # turn whatever `code_branch` is into a commit hash
            branch = self._repo.branch(self._code_branch)
            self._deploy_ref = branch.commit.sha
        return self._deploy_ref


def _get_github():
    try:
        from .config import GITHUB_APIKEY
    except ImportError:
        print (
            "You can add a GitHub API key to automate this step:\n"
            "    $ cp {project_root}/config.example.py {project_root}/config.py\n"
            "Then edit {project_root}/config.py"
        ).format(project_root=PROJECT_ROOT)
        username = raw_input('Github username: ')
        password = getpass('Github password: ')
        return login(
            username=username,
            password=password,
        )
    else:
        return login(
            token=GITHUB_APIKEY,
        )
