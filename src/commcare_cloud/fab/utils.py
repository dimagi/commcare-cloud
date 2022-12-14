from __future__ import absolute_import, print_function, unicode_literals

import datetime
import os
import pickle
import re
import sys
import traceback
from io import open

from fabric.api import env, execute
from fabric.operations import sudo
from github import UnknownObjectException, Github
from memoized import memoized_property

from .const import (
    CACHED_DEPLOY_CHECKPOINT_FILENAME,
    CACHED_DEPLOY_ENV_FILENAME,
    PROJECT_ROOT,
)
from commcare_cloud.github import github_repo


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


def _get_checkpoint_filename():
    return '{}_{}'.format(env.deploy_env, CACHED_DEPLOY_CHECKPOINT_FILENAME)


def _get_env_filename(env_name):
    return '{}_{}'.format(env_name, CACHED_DEPLOY_ENV_FILENAME)


def cache_deploy_state(command_index):
    with open(os.path.join(PROJECT_ROOT, _get_checkpoint_filename()), 'wb') as f:
        pickle.dump(command_index, f)
    with open(os.path.join(PROJECT_ROOT, _get_env_filename(env.deploy_env)), 'wb') as f:
        pickle.dump(env, f)


def clear_cached_deploy():
    os.remove(os.path.join(PROJECT_ROOT, _get_checkpoint_filename()))
    os.remove(os.path.join(PROJECT_ROOT, _get_env_filename(env.deploy_env)))


def retrieve_cached_deploy_env(env_name):
    filename = os.path.join(PROJECT_ROOT, _get_env_filename(env_name))
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


def get_changelogs_in_date_range(since, until, get_file_fn=None):
    """
    This generates the list of changelogs in a given daterange
        from the changelog index file in commacare-cloud github repo.

    This relies on the fact that 'hosting_docs/source/changelog/index.md'
        contains below style header for each dated changelog and its docs link.
        #### **2022-11-08** [kafka-upgrade-to-3.2.3](0062-kafka-upgrade.md)

    A bit hacky since we don't have an actual changelog feed
    """
    def _get_file_content_as_lines():
        repo = Github().get_repo("dimagi/commcare-cloud")
        CHANGELOG_INDEX = "hosting_docs/source/changelog/index.md"
        return str(repo.get_contents(CHANGELOG_INDEX).decoded_content).split("\\n")

    file_content = _get_file_content_as_lines() if not get_file_fn  else get_file_fn()
    search_dates = [
        (since + datetime.timedelta(day)).strftime('%Y-%m-%d')
        for day in range((until - since).days + 1)
    ]
    regex = r"({}).*\((.*)\.md\)".format("|".join(search_dates))
    base_url = "https://commcare-cloud.readthedocs.io/en/latest/changelog"
    changelogs = []
    for line in file_content:
        matches = re.findall(regex, line)
        if matches:
            changelogs.append("{}/{}.html".format(base_url, matches[0][1]))
    return changelogs
