#!/usr/bin/env python
# -*- coding: utf-8 -*-
"""
Server layout:
    ~/www/
        This folder contains the code, python environment, and logs
        for each environment (staging, production, etc) running on the server.
        Each environment has its own subfolder named for its evironment
        (i.e. ~/www/staging/log and ~/www/production/log).

    ~/www/<environment>/releases/<YYYY-MM-DD-HH.SS>
        This folder contains a release of commcarehq. Each release has its own
        virtual environment that can be found in `python_env`.

    ~/www/<environment>/current
        This path is a symlink to the release that is being run
        (~/www/<environment>/releases<YYYY-MM-DD-HH.SS>).

    ~/www/<environment>/current/services/
        This contains two subfolders
            /supervisor/
        which hold the configurations for these applications
        for each environment (staging, production, etc) running on the server.
        Theses folders are included in the global /etc/apache2 and
        /etc/supervisor configurations.

"""
from __future__ import absolute_import
from __future__ import print_function
from __future__ import unicode_literals

import functools
import os
import pipes
import posixpath

from fabric import utils
from fabric.api import env, execute, parallel, roles, sudo, task
from fabric.colors import blue, magenta, red
from fabric.context_managers import cd
from fabric.contrib import console
from fabric.operations import require
from github import GithubException

from commcare_cloud.environment.main import get_environment
from commcare_cloud.environment.paths import get_available_envs
from commcare_cloud.github import github_repo
from .checks import check_servers
from .const import ROLES_ALL_SERVICES, ROLES_DEPLOY, ROLES_DJANGO, ROLES_PILLOWTOP
from .exceptions import PreindexNotFinished
from .operations import db
from .operations import release, staticfiles, supervisor
from .utils import (
    cache_deploy_state,
    clear_cached_deploy,
    execute_with_timing,
    retrieve_cached_deploy_checkpoint,
    retrieve_cached_deploy_env,
    traceback_string,
)

if env.ssh_config_path and os.path.isfile(os.path.expanduser(env.ssh_config_path)):
    env.use_ssh_config = True

env.abort_exception = Exception
env.linewise = True
env.colorize_errors = True
env.always_use_pty = False
env['sudo_prefix'] += '-H '


env.roledefs = {
    'django_celery': [],
    'django_app': [],
    # for now combined with celery
    'django_pillowtop': [],
    # 'django_celery, 'django_app', and 'django_pillowtop' all in one
    # use this ONLY for single server config,
    # otherwise deploy() will run multiple times in parallel causing issues
    'django_monolith': [],

    'staticfiles': [],

    # package level configs that are not quite config'ed yet in this fabfile
    'couch': [],
    'pg': [],
    'lb': [],
    # need a special 'deploy' role to make deploy only run once
    'deploy': [],
}


def _require_target():
    require('root', 'code_root', 'hosts', 'deploy_env',
            provided_by=('staging', 'production', 'softlayer'))


def _setup_path():
    # using posixpath to ensure unix style slashes.
    # See bug-ticket: http://code.fabfile.org/attachments/61/posixpath.patch
    env.root = posixpath.join(env.home, 'www', env.deploy_env)
    env.log_dir = posixpath.join(env.home, 'www', env.deploy_env, 'log')
    env.releases = posixpath.join(env.root, 'releases')
    env.code_current = posixpath.join(env.root, 'current')
    env.code_root = posixpath.join(env.releases, env.ccc_environment.new_release_name())
    env.project_root = posixpath.join(env.code_root, env.project)
    env.project_media = posixpath.join(env.code_root, 'media')

    # TODO remove when machines are no longer running Python 3.6
    python_env = "python_env-3.6" if env.ccc_environment.python_version == "3.6" else "python_env"

    env.virtualenv_current = posixpath.join(env.code_current, python_env)
    env.virtualenv_root = posixpath.join(env.code_root, python_env)

    env.services = posixpath.join(env.code_root, 'services')
    env.db = '%s_%s' % (env.project, env.deploy_env)


def load_env():
    env.ccc_environment = get_environment(env.env_name)
    vars_not_to_overwrite = {key: value for key, value in env.items()
                             if key not in ('sudo_user', 'keepalive')}

    vars = env.ccc_environment.app_processes_config.to_json()
    vars.update(env.ccc_environment.fab_settings_config.to_json())
    # Variables that were already in `env`
    # take precedence over variables set in app-processes.yml
    # except a short blacklist that we expect app-processes.yml vars to overwrite
    overlap = set(vars_not_to_overwrite) & set(vars)
    for key in overlap:
        print(f'NOTE: ignoring app-processes.yml var {key}={vars[key]!r}. '
              f'Using value {vars_not_to_overwrite[key]!r} instead.')
    vars.update(vars_not_to_overwrite)
    env.update(vars)
    env.deploy_env = env.ccc_environment.meta_config.deploy_env


def _setup_env(env_name):
    env.env_name = env_name
    load_env()
    _set_code_branch(env.default_branch)
    execute(env_common)


def _set_code_branch(default_branch):
    if not getattr(env, 'code_branch', None):
        env.code_branch = default_branch
    print("Using commcare-hq branch {}".format(env.code_branch))


def env_common():
    servers = env.ccc_environment.sshable_hostnames_by_group

    env.is_monolith = len(set(servers['all']) - set(servers['control'])) < 2

    # turn whatever `code_branch` is into a commit hash
    env.deploy_ref = github_repo('dimagi/commcare-hq').get_commit(env.code_branch).sha

    _setup_path()

    all = servers['all']
    staticfiles = servers.get('staticfiles', servers['proxy'])
    webworkers = servers['webworkers']
    django_manage = servers.get('django_manage', [webworkers[0]])
    postgresql = servers['postgresql']
    pg_standby = servers.get('pg_standby', [])
    formplayer = servers['formplayer']
    elasticsearch = servers['elasticsearch']
    celery = servers['celery']
    # if no server specified, just don't run pillowtop
    pillowtop = servers.get('pillowtop', [])

    deploy = servers.get('deploy', servers['webworkers'])[:1]

    if len(staticfiles) > 1 and not env.use_shared_dir_for_staticfiles:
        utils.abort(
            "There should be only one 'staticfiles' host. "
            "Ensure that only one host is assigned to the 'staticfiles' group, "
            "or enable use_shared_dir_for_staticfiles."
        )

    env.roledefs = {
        'all': all,
        'pg': postgresql,
        'pgstandby': pg_standby,
        'elasticsearch': elasticsearch,
        'django_celery': celery,
        'django_app': webworkers,
        'django_manage': django_manage,
        'django_pillowtop': pillowtop,
        'formplayer': formplayer,
        'staticfiles': staticfiles,
        'staticfiles_primary': [staticfiles[0]],
        'lb': [],
        # 'deploy' contains a single server, one that commcare-hq is deployed to.
        # having deploy here makes it so that
        # we don't get prompted for a host or run deploy too many times
        'deploy': deploy,
        # fab complains if this doesn't exist
        'django_monolith': [],
        'control': servers.get('control')[:1],
    }
    env.roles = ['deploy']
    env.hosts = env.roledefs['deploy']
    env.resume = False
    env.full_deploy = False
    env.supervisor_roles = ROLES_ALL_SERVICES


@task
def webworkers():
    env.supervisor_roles = ROLES_DJANGO


@task
def pillowtop():
    env.supervisor_roles = ROLES_PILLOWTOP


@task
@roles(ROLES_PILLOWTOP)
def preindex_views():
    """
    Creates a new release that runs preindex_everything. Clones code from
    `current` release and updates it.
    """
    _setup_release()
    db.preindex_views()


@roles(ROLES_DEPLOY)
def send_email(subject, message, use_current_release=False):
    code_dir = env.code_current if use_current_release else env.code_root
    virtualenv_dir = env.virtualenv_current if use_current_release else env.virtualenv_root
    with cd(code_dir):
        sudo(
            f'{virtualenv_dir}/bin/python manage.py '
            f'send_email --to-admins --subject {pipes.quote(subject)} {pipes.quote(message)}'
        )


@task
def kill_stale_celery_workers():
    """OBSOLETE use 'kill-stale-celery-workers' instead"""
    print(kill_stale_celery_workers.__doc__)


@task
def rollback_formplayer():
    print(red("This command is now implemented with ansible:"))
    print("cchq {} ansible-playbook rollback_formplayer.yml --tags=rollback".format(env.deploy_env))


def parse_int_or_exit(val):
    try:
        return int(val)
    except (ValueError, TypeError):
        print(red("Unable to parse '{}' into an integer".format(val)))
        exit()


@task
def setup_limited_release(keep_days=1):
    """ Sets up a release on a single machine
    defaults to webworkers:0

    See :func:`_setup_release` for more info

    Example:
    fab <env> setup_limited_release:keep_days=10  # Makes a new release that will last for 10 days
    fab <env> setup_limited_release --set code_branch=<HQ BRANCH>
    """
    _setup_release(parse_int_or_exit(keep_days), full_cluster=False)


@task
def setup_release(keep_days=0):
    """ Sets up a full release across the cluster

    See :func:`_setup_release` for info

    Example:
    fab <env> setup_release:keep_days=10  # Makes a new release that will last for 10 days
    """

    _setup_release(parse_int_or_exit(keep_days), full_cluster=True)


def _setup_release(keep_days=2, full_cluster=True):
    """
    Setup a release in the releases directory with the most recent code.
    Useful for running management commands. These releases will automatically
    be cleaned up at the finish of each deploy. To ensure that a release will
    last past a deploy use the `keep_days` param.

    More options at
    https://github.com/dimagi/commcare-cloud/blob/master/src/commcare_cloud/fab/README.md#private-releases

    :param keep_days: The number of days to keep this release before it will be purged
    :param full_cluster: If False, only setup on webworkers[0] where the command will be run
    """
    execute_with_timing(release.create_code_dir(full_cluster))
    update_code = release.update_code(full_cluster)
    execute_with_timing(update_code, env.deploy_ref)
    execute_with_timing(release.update_virtualenv(full_cluster))
    execute_with_timing(copy_release_files, full_cluster)

    if keep_days > 0:
        execute_with_timing(release.mark_keep_until(full_cluster), keep_days)

    print(blue("Your private release is located here: "))
    print(blue(env.code_root))


def conditionally_stop_pillows_and_celery_during_migrate():
    """
    Conditionally stops pillows and celery if any migrations exist
    """
    if all(execute(db.migrations_exist).values()):
        execute_with_timing(supervisor.stop_pillows)
        execute(db.set_in_progress_flag)
        execute_with_timing(supervisor.stop_celery_tasks)
    execute_with_timing(db.migrate)


def deploy_checkpoint(command_index, command_name, fn, *args, **kwargs):
    """
    Stores fabric env in redis and then runs the function if it shouldn't be skipped
    """
    if env.resume and command_index < env.checkpoint_index:
        print(blue("Skipping command: '{}'".format(command_name)))
        return
    fn(*args, **kwargs)
    cache_deploy_state(command_index + 1)


def _deploy_without_asking(skip_record):
    try:
        for index, command in enumerate(ONLINE_DEPLOY_COMMANDS):
            deploy_checkpoint(index, command.__name__, execute_with_timing, command)
    except PreindexNotFinished:
        send_email(
            " You can't deploy to {} yet. There's a preindex in process.".format(env.env_name),
            ("Preindexing is taking a while, so hold tight "
             "and wait for an email saying it's done. "
             "Thank you for using AWESOME DEPLOY.")
        )
        raise
    except Exception:
        execute_with_timing(
            send_email,
            "Deploy to {environment} failed. Try resuming with "
            "fab {environment} deploy:resume=yes.".format(environment=env.env_name),
            traceback_string()
        )
        # hopefully bring the server back to life
        silent_services_restart()
        raise
    else:
        execute(check_servers.perform_system_checks)
        execute_with_timing(release.update_current)
        silent_services_restart()
        if skip_record == 'no':
            execute_with_timing(release.record_successful_release)
        clear_cached_deploy()


@task
def update_current(release=None):
    execute(release.update_current, release)


def copy_release_files(full_cluster=True):
    execute(release.copy_localsettings(full_cluster))
    if full_cluster:
        execute(release.copy_components)
        execute(release.copy_node_modules)
        execute(release.copy_compressed_js_staticfiles)


@task
def rollback():
    """
    Rolls back the servers to the previous release if it exists and is same
    across servers.
    """
    number_of_releases = execute(release.get_number_of_releases)
    if not all(n > 1 for n in number_of_releases):
        print(red('Aborting because there are not enough previous releases.'))
        exit()

    releases = execute(release.get_previous_release)

    unique_releases = set(releases.values())
    if len(unique_releases) != 1:
        print(red('Aborting because not all hosts would rollback to same release'))
        exit()

    unique_release = unique_releases.pop()

    if not unique_release:
        print(red('Aborting because release path is empty. '
                  'This probably means there are no releases to rollback to.'))
        exit()

    if not console.confirm('Do you wish to rollback to release: {}'.format(unique_release), default=False):
        print(blue('Exiting.'))
        exit()

    exists = execute(release.ensure_release_exists, unique_release)

    if all(exists.values()):
        print(blue('Updating current and restarting services'))
        execute(release.update_current, unique_release)
        silent_services_restart(use_current_release=True)
        execute(release.mark_last_release_unsuccessful)
    else:
        print(red('Aborting because not all hosts have release'))
        exit()


@task
def clean_releases(keep=3):
    """
    Cleans old and failed deploys from the ~/www/<environment>/releases/ directory
    """
    execute(release.clean_releases, keep)


@task
@roles(['deploy'])
def manage(cmd=None):
    """OBSOLETE use 'django-manage' instead"""
    exit(manage.__doc__)


@task
def deploy_commcare(resume='no', skip_record='no'):
    """Preindex and deploy if it completes quickly enough, otherwise abort
    fab <env> deploy_commcare:resume=yes  # resume from previous deploy
    fab <env> deploy_commcare:skip_record=yes  # skip record_successful_release
    """
    _require_target()

    env.full_deploy = True

    if resume == 'yes':
        try:
            cached_payload = retrieve_cached_deploy_env(env.deploy_env)
            checkpoint_index = retrieve_cached_deploy_checkpoint()
        except Exception:
            print(red('Unable to resume deploy, please start anew'))
            raise
        env.update(cached_payload)
        env.resume = True
        env.checkpoint_index = checkpoint_index or 0
        print(magenta('You are about to resume the deploy in {}'.format(env.code_root)))

    _deploy_without_asking(skip_record)


@task
@parallel
def supervisorctl(command):
    require('supervisor_roles',
            provided_by=('staging', 'production', 'softlayer'))

    @roles(env.supervisor_roles)
    def _inner():
        supervisor.supervisor_command(command)

    execute(_inner)


@roles(ROLES_ALL_SERVICES)
def services_stop():
    """Stop the gunicorn servers"""
    _require_target()
    supervisor.supervisor_command('stop all')


@task
def restart_services():
    _require_target()
    if not console.confirm('Are you sure you want to restart the services on '
                           '{env.deploy_env}?'.format(env=env), default=False):
        utils.abort('Task aborted.')

    silent_services_restart(use_current_release=True)


def silent_services_restart(use_current_release=False):
    """
    Restarts services and sets the in progress flag so that pingdom doesn't yell falsely
    """
    execute(db.set_in_progress_flag, use_current_release)
    if not env.is_monolith:
        execute(supervisor.restart_all_except_webworkers)
    execute(supervisor.restart_webworkers)


@task
def stop_celery():
    execute(supervisor.stop_celery_tasks, True)


@task
def start_celery():
    execute(supervisor.start_celery_tasks, True)


@task
def restart_webworkers():
    execute(supervisor.restart_webworkers)


@task
def stop_pillows():
    execute(supervisor.stop_pillows, True)


@task
def start_pillows():
    execute(supervisor.start_pillows, True)


@roles(ROLES_PILLOWTOP)
def reset_pillow(pillow):
    _require_target()
    prefix = 'commcare-hq-{}-pillowtop'.format(env.deploy_env)
    supervisor.supervisor_command('stop {prefix}-{pillow}'.format(
        prefix=prefix,
        pillow=pillow
    ))
    with cd(env.code_root):
        sudo(f'{env.virtualenv_root}/bin/python manage.py ptop_reset_checkpoint {pillow} --noinput')
    supervisor.supervisor_command('start {prefix}-{pillow}'.format(
        prefix=prefix,
        pillow=pillow
    ))


ONLINE_DEPLOY_COMMANDS = [
    _setup_release,
    db.preindex_views,
    db.ensure_preindex_completion,
    db.ensure_checkpoints_safe,
    staticfiles.yarn_install,
    staticfiles.version_static,     # run after any new bower code has been installed
    staticfiles.collectstatic,
    staticfiles.compress,
    staticfiles.update_translations,
    conditionally_stop_pillows_and_celery_during_migrate,
    db.create_kafka_topics,
    db.flip_es_aliases,
    staticfiles.pull_manifest,
    staticfiles.pull_staticfiles_cache,
    release.clean_releases,
]


@task
def check_status():
    """OBSOLETE replaced by

    commcare-cloud <env> ping all
    commcare-cloud <env> service postgresql status
    commcare-cloud <env> service elasticsearch status
    """
    exit(check_status.__doc__)


@task
def perform_system_checks():
    """OBSOLETE use 'perform-system-checks' instead"""
    exit(perform_system_checks.__doc__)


def make_tasks_for_envs(available_envs):
    tasks = {}
    for env_name in available_envs:
        environment = get_environment(env_name)
        if not environment.meta_config.bare_non_cchq_environment:
            tasks[env_name] = task(alias=env_name)(functools.partial(_setup_env, env_name))
            tasks[env_name].__doc__ = environment.proxy_config['SITE_HOST']
    return tasks


# Automatically create a task for each environment
locals().update(make_tasks_for_envs(get_available_envs()))
