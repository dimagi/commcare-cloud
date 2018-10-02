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
import datetime
import functools
import os
import posixpath
from getpass import getpass

import pipes
import pytz
from distutils.util import strtobool

from fabric import utils
from fabric.api import run, roles, execute, task, sudo, env, parallel
from fabric.colors import blue, red, magenta
from fabric.context_managers import cd
from fabric.contrib import files, console
from fabric.operations import require

from commcare_cloud.environment.main import get_environment
from commcare_cloud.environment.paths import get_available_envs

from .const import (
    ROLES_ALL_SRC,
    ROLES_ALL_SERVICES,
    ROLES_PILLOWTOP,
    ROLES_DJANGO,
    ROLES_DEPLOY,
)
from .exceptions import PreindexNotFinished
from .operations import (
    db,
    staticfiles,
    supervisor,
    formplayer,
    release,
    offline as offline_ops,
    airflow
)
from .utils import (
    DeployMetadata,
    cache_deploy_state,
    clear_cached_deploy,
    execute_with_timing,
    retrieve_cached_deploy_checkpoint,
    retrieve_cached_deploy_env,
    traceback_string,
)
from .checks import (
    check_servers,
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
    'rabbitmq': [],
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
    env.code_root = posixpath.join(env.releases, env.deploy_metadata.timestamp)
    env.project_root = posixpath.join(env.code_root, env.project)
    env.project_media = posixpath.join(env.code_root, 'media')
    env.virtualenv_current = posixpath.join(env.code_current, 'python_env')
    env.virtualenv_root = posixpath.join(env.code_root, 'python_env')
    env.services = posixpath.join(env.code_root, 'services')
    env.jython_home = '/usr/local/lib/jython'
    env.db = '%s_%s' % (env.project, env.deploy_env)
    env.offline_releases = posixpath.join('/home/{}/releases'.format(env.user))
    env.offline_code_dir = posixpath.join('{}/{}'.format(env.offline_releases, 'offline'))


def _override_code_root_to_current():
    env.code_root = env.code_current
    env.project_root = posixpath.join(env.code_root, env.project)
    env.project_media = posixpath.join(env.code_root, 'media')
    env.virtualenv_current = posixpath.join(env.code_current, 'python_env')
    env.virtualenv_root = posixpath.join(env.code_root, 'python_env')
    env.services = posixpath.join(env.code_root, 'services')


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
        print('NOTE: ignoring app-processes.yml var {}={!r}. Using value {!r} instead.'.format(key, vars[key], vars_not_to_overwrite[key]))
    vars.update(vars_not_to_overwrite)
    env.update(vars)
    env.deploy_env = env.ccc_environment.meta_config.deploy_env


def _setup_env(env_name):
    env.env_name = env_name
    load_env()
    _confirm_branch(env.default_branch)
    _confirm_environment_time(env_name)
    execute(env_common)
    execute(_confirm_deploying_same_code)


def _confirm_branch(default_branch='master'):
    if not hasattr(env, 'code_branch'):
        print("code_branch not specified, using '{}'. "
              "You can override this with '--set code_branch=<branch>'"
              .format(default_branch))
        env.code_branch = default_branch

    if env.code_branch != default_branch:
        branch_message = (
            "Whoa there bud! You're using branch {env.code_branch}. "
            "ARE YOU DOING SOMETHING EXCEPTIONAL THAT WARRANTS THIS?"
        ).format(env=env)
        if not console.confirm(branch_message, default=False):
            utils.abort('Action aborted.')


def _confirm_environment_time(env_name):
    window = env.acceptable_maintenance_window
    if window:
        d = datetime.datetime.now(pytz.timezone(window['timezone']))
        if window['hour_start'] <= d.hour < window['hour_end']:
            return
    else:
        return

    message = (
        "Whoa there bud! You're deploying '%s' during the day. "
        "The current local time is %s.\n"
        "ARE YOU DOING SOMETHING EXCEPTIONAL THAT WARRANTS THIS?"
    ) % (env_name, d.strftime("%-I:%M%p on %h. %d %Z"))
    if not console.confirm(message, default=False):
        utils.abort('Action aborted.')


def _confirm_deploying_same_code():
    if env.deploy_metadata.current_ref_is_different_than_last:
        return

    if env.code_branch == 'master':
        branch_specific_msg = "Perhaps you meant to merge a PR or specify a --set code_branch=<branch> ?"
    elif env.code_branch == 'enterprise':
        branch_specific_msg = (
            "Have you tried rebuilding the enterprise branch (in HQ directory)? "
            "./scripts/rebuildstaging --enterprise"
        )
    elif env.code_branch == 'autostaging':
        branch_specific_msg = (
            "Have you tried rebuilding the autostaging branch (in HQ directory)? "
            "./scripts/rebuildstaging"
        )
    else:
        branch_specific_msg = (
            "Did you specify the correct branch using --set code_branch=<branch> ?"
        )

    message = (
        "Whoa there bud! You're deploying {code_branch} which happens to be "
        "the same code as was previously deployed to this environment.\n"
        "{branch_specific_msg}\n"
        "Is this intentional?"
    ).format(code_branch=env.code_branch, branch_specific_msg=branch_specific_msg)
    if not console.confirm(message, default=False):
        utils.abort('Action aborted.')


def env_common():
    servers = env.ccc_environment.sshable_hostnames_by_group

    env.is_monolith = len(set(servers['all']) - set(servers['control'])) < 2

    env.deploy_metadata = DeployMetadata(env.code_branch, env.deploy_env)
    _setup_path()

    all = servers['all']
    proxy = servers['proxy']
    webworkers = servers['webworkers']
    django_manage = servers.get('django_manage', [webworkers[0]])
    riakcs = servers.get('riakcs', [])
    postgresql = servers['postgresql']
    pg_standby = servers.get('pg_standby', [])
    formplayer = servers['formplayer']
    elasticsearch = servers['elasticsearch']
    celery = servers['celery']
    rabbitmq = servers['rabbitmq']
    # if no server specified, just don't run pillowtop
    pillowtop = servers.get('pillowtop', [])
    airflow = servers.get('airflow', [])

    deploy = servers.get('deploy', servers['webworkers'])[:1]

    env.roledefs = {
        'all': all,
        'pg': postgresql,
        'pgstandby': pg_standby,
        'elasticsearch': elasticsearch,
        'riakcs': riakcs,
        'rabbitmq': rabbitmq,
        'django_celery': celery,
        'django_app': webworkers,
        'django_manage': django_manage,
        'django_pillowtop': pillowtop,
        'formplayer': formplayer,
        'staticfiles': proxy,
        'lb': [],
        # having deploy here makes it so that
        # we don't get prompted for a host or run deploy too many times
        'deploy': deploy,
        # fab complains if this doesn't exist
        'django_monolith': [],
        'control': servers.get('control')[:1],
        'airflow': airflow
    }
    env.roles = ['deploy']
    env.hosts = env.roledefs['deploy']
    env.resume = False
    env.offline = False
    env.supervisor_roles = ROLES_ALL_SRC


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
def mail_admins(subject, message, use_current_release=False):
    code_dir = env.code_current if use_current_release else env.code_root
    virtualenv_dir = env.virtualenv_current if use_current_release else env.virtualenv_root
    with cd(code_dir):
        sudo((
            '%(virtualenv_dir)s/bin/python manage.py '
            'mail_admins --subject %(subject)s %(message)s --slack --environment %(deploy_env)s'
        ) % {
            'virtualenv_dir': virtualenv_dir,
            'subject': pipes.quote(subject),
            'message': pipes.quote(message),
            'deploy_env': pipes.quote(env.deploy_env),
        })


@task
def hotfix_deploy():
    """
    deploy ONLY the code with no extra cleanup or syncing

    for small python-only hotfixes

    """
    if not console.confirm('Are you sure you want to deploy to {env.deploy_env}?'.format(env=env), default=False) or \
       not console.confirm('Did you run "fab {env.deploy_env} preindex_views"? '.format(env=env), default=False) or \
       not console.confirm('HEY!!!! YOU ARE ONLY DEPLOYING CODE. THIS IS NOT A NORMAL DEPLOY. COOL???', default=False):
        utils.abort('Deployment aborted.')

    _require_target()
    run('echo ping!')  # workaround for delayed console response
    try:
        execute(release.update_code(full_cluster=True), env.deploy_metadata.deploy_ref, True)
    except Exception:
        execute(
            mail_admins,
            "Deploy failed",
            traceback_string()
        )
        # hopefully bring the server back to life
        silent_services_restart(use_current_release=True)
        raise
    else:
        silent_services_restart(use_current_release=True)
        execute(release.record_successful_deploy)


def _confirm_translated():
    if datetime.datetime.now().isoweekday() != 2 or env.deploy_env != 'production':
        return True
    return console.confirm(
        "It's Tuesday, did you update the translations from transifex? "
        "Try running this handy script from the root of your commcare-hq directory:\n./scripts/update-translations.sh\n"
    )


@task
def kill_stale_celery_workers():
    """
    Kills celery workers that failed to properly go into warm shutdown
    """
    execute(release.kill_stale_celery_workers)


@task
def deploy_formplayer():
    execute(announce_formplayer_deploy_start)
    execute(formplayer.build_formplayer, True)
    execute(supervisor.restart_formplayer)


@task
def rollback_formplayer():
    execute(formplayer.rollback_formplayer)
    execute(supervisor.restart_formplayer)


@task
def offline_setup_release(keep_days=0):
    env.offline = True
    execute_with_timing(release.create_offline_dir)
    execute_with_timing(release.sync_offline_dir)

    execute_with_timing(release.create_code_dir)
    execute_with_timing(release.update_code_offline)

    execute_with_timing(release.clone_virtualenv)
    execute_with_timing(copy_release_files)

    execute_with_timing(release.update_bower_offline)
    execute_with_timing(release.update_npm_offline)


@task
def prepare_offline_deploy():
    offline_ops.prepare_files()
    offline_ops.prepare_formplayer_build()


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


def _setup_release(keep_days=0, full_cluster=True):
    """
    Setup a release in the releases directory with the most recent code.
    Useful for running management commands. These releases will automatically
    be cleaned up at the finish of each deploy. To ensure that a release will
    last past a deploy use the `keep_days` param.

    :param keep_days: The number of days to keep this release before it will be purged
    :param full_cluster: If False, only setup on webworkers[0] where the command will be run
    """
    deploy_ref = env.deploy_metadata.deploy_ref  # Make sure we have a valid commit
    env.deploy_metadata.tag_setup_release()
    execute_with_timing(release.create_code_dir(full_cluster))
    execute_with_timing(release.update_code(full_cluster), deploy_ref)
    execute_with_timing(release.update_virtualenv(full_cluster))

    execute_with_timing(copy_release_files, full_cluster)

    if keep_days > 0:
        execute_with_timing(release.mark_keep_until(full_cluster), keep_days)

    print(blue("Your private release is located here: "))
    print(blue(env.code_root))


@task
def apply_patch(patchfile=None):
    """
    Used to apply a git patch created via `git format-patch`. Usage:

        fab <env> apply_patch:patchfile=/path/to/patch

    Note: Only use this when absolutely necessary. Normally we should use regular
    deploy. This is only used for patching when we do not have access to the Internet.
    """
    if not patchfile:
        print(red("Must specify patch filepath"))
        exit()
    execute(release.apply_patch, patchfile)
    silent_services_restart(use_current_release=True)


@task
def reverse_patch(patchfile=None):
    """
    Used to reverse a git patch created via `git format-patch`. Usage:

        fab <env> reverse_patch:patchfile=/path/to/patch

    Note: Only use this when absolutely necessary. Normally we should use regular
    deploy. This is only used for patching when we do not have access to the Internet.
    """
    if not patchfile:
        print(red("Must specify patch filepath"))
        exit()
    execute(release.reverse_patch, patchfile)
    silent_services_restart(use_current_release=True)


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
    cache_deploy_state(command_index)
    fn(*args, **kwargs)


def announce_deploy_start():
    if env.email_enabled:
        execute_with_timing(
            mail_admins,
            "{user} has initiated a deploy to {environment}.".format(
                user=env.user,
                environment=env.deploy_env,
            ),
            ''
        )


def announce_formplayer_deploy_start():
    execute_with_timing(
        mail_admins,
        "{user} has initiated a formplayer deploy to {environment}.".format(
            user=env.user,
            environment=env.deploy_env,
        ),
        '',
        use_current_release=True,
    )


def _deploy_without_asking(skip_record):
    if env.offline:
        commands = OFFLINE_DEPLOY_COMMANDS
    else:
        commands = ONLINE_DEPLOY_COMMANDS

    try:
        for index, command in enumerate(commands):
            deploy_checkpoint(index, command.__name__, execute_with_timing, command)
    except PreindexNotFinished:
        mail_admins(
            " You can't deploy to {} yet. There's a preindex in process.".format(env.env_name),
            ("Preindexing is taking a while, so hold tight "
             "and wait for an email saying it's done. "
             "Thank you for using AWESOME DEPLOY.")
        )
    except Exception:
        execute_with_timing(
            mail_admins,
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
            execute_with_timing(release.record_successful_deploy)
        clear_cached_deploy()


@task
def update_current(release=None):
    execute(release.update_current, release)


@task
@roles(ROLES_ALL_SRC)
@parallel
def unlink_current():
    """
    Unlinks the current code directory. Use with caution.
    """
    message = 'Are you sure you want to unlink the current release of {env.deploy_env}?'.format(env=env)

    if not console.confirm(message, default=False):
        utils.abort('Deployment aborted.')

    if files.exists(env.code_current):
        sudo('unlink {}'.format(env.code_current))


def copy_release_files(full_cluster=True):
    execute(release.copy_localsettings(full_cluster))
    if full_cluster:
        execute(release.copy_tf_localsettings)
        execute(release.copy_formplayer_properties)
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
def clean_offline_releases():
    """
    Cleans all releases in home directory
    """
    execute(release.clean_offline_releases)


@task
def force_update_static():
    _require_target()
    execute(staticfiles.collectstatic, use_current_release=True)
    execute(staticfiles.compress, use_current_release=True)
    execute(staticfiles.update_manifest, use_current_release=True)
    silent_services_restart(use_current_release=True)


@task
@roles(['deploy'])
def manage(cmd):
    """
    run a management command

    usage:
        fab <env> manage:<command>
    e.g.
        fab production manage:'prune_couch_views --noinput'
    """
    _require_target()
    with cd(env.code_current):
        sudo('{env.virtualenv_current}/bin/python manage.py {cmd}'
             .format(env=env, cmd=cmd))


@task(alias='deploy')
def awesome_deploy(confirm="yes", resume='no', offline='no', skip_record='no'):
    """Preindex and deploy if it completes quickly enough, otherwise abort
    fab <env> deploy:confirm=no  # do not confirm
    fab <env> deploy:resume=yes  # resume from previous deploy
    fab <env> deploy:offline=yes  # offline deploy
    fab <env> deploy:skip_record=yes  # skip record_successful_release
    """
    _require_target()
    if strtobool(confirm) and (
        not _confirm_translated() or
        not console.confirm(
            'Are you sure you want to preindex and deploy to '
            '{env.deploy_env}?'.format(env=env), default=False)
    ):
        utils.abort('Deployment aborted.')

    if resume == 'yes':
        try:
            cached_payload = retrieve_cached_deploy_env()
            checkpoint_index = retrieve_cached_deploy_checkpoint()
        except Exception:
            print(red('Unable to resume deploy, please start anew'))
            raise
        env.update(cached_payload)
        env.resume = True
        env.checkpoint_index = checkpoint_index or 0
        print(magenta('You are about to resume the deploy in {}'.format(env.code_root)))

    if datetime.datetime.now().isoweekday() == 5:
        warning_message = 'Friday'
    else:
        warning_message = ''

    env.offline = offline == 'yes'

    if env.offline:
        print(magenta(
            'You are about to run an offline deploy.'
            'Ensure that you have run `fab prepare_offline_deploy`.'
        ))
        offline_ops.check_ready()
        if not console.confirm('Are you sure you want to do an offline deploy?'.format(default=False)):
            utils.abort('Task aborted')

        # Force ansible user and prompt for password
        env.user = 'ansible'
        env.password = getpass('Enter the password for the ansbile user: ')

    if warning_message:
        print('')
        print('┓┏┓┏┓┃')
        print('┛┗┛┗┛┃＼○／')
        print('┓┏┓┏┓┃  /      ' + warning_message)
        print('┛┗┛┗┛┃ノ)')
        print('┓┏┓┏┓┃         deploy,')
        print('┛┗┛┗┛┃')
        print('┓┏┓┏┓┃         good')
        print('┛┗┛┗┛┃')
        print('┓┏┓┏┓┃         luck!')
        print('┃┃┃┃┃┃')
        print('┻┻┻┻┻┻')

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
def stop_pillows():
    execute(supervisor.stop_pillows, True)


@task
def start_pillows():
    execute(supervisor.start_pillows, True)


@task
def reset_mvp_pillows():
    _require_target()
    _setup_release()
    mvp_pillows = [
        'MVPFormIndicatorPillow',
        'MVPCaseIndicatorPillow',
    ]
    for pillow in mvp_pillows:
        reset_pillow(pillow)


@roles(ROLES_PILLOWTOP)
def reset_pillow(pillow):
    _require_target()
    prefix = 'commcare-hq-{}-pillowtop'.format(env.deploy_env)
    supervisor.supervisor_command('stop {prefix}-{pillow}'.format(
        prefix=prefix,
        pillow=pillow
    ))
    with cd(env.code_root):
        command = '{virtualenv_root}/bin/python manage.py ptop_reset_checkpoint {pillow} --noinput'.format(
            virtualenv_root=env.virtualenv_root,
            pillow=pillow,
        )
        sudo(command)
    supervisor.supervisor_command('start {prefix}-{pillow}'.format(
        prefix=prefix,
        pillow=pillow
    ))


ONLINE_DEPLOY_COMMANDS = [
    _setup_release,
    announce_deploy_start,
    db.preindex_views,
    # Compute version statics while waiting for preindex
    staticfiles.prime_version_static,
    db.ensure_preindex_completion,
    db.ensure_checkpoints_safe,
    staticfiles.version_static,
    staticfiles.bower_install,
    staticfiles.npm_install,
    staticfiles.collectstatic,
    staticfiles.compress,
    staticfiles.update_translations,
    formplayer.build_formplayer,
    conditionally_stop_pillows_and_celery_during_migrate,
    db.create_kafka_topics,
    db.flip_es_aliases,
    staticfiles.update_manifest,
    release.clean_releases,
]

OFFLINE_DEPLOY_COMMANDS = [
    offline_setup_release,
    db.preindex_views,
    # Compute version statics while waiting for preindex
    staticfiles.prime_version_static,
    db.ensure_preindex_completion,
    db.ensure_checkpoints_safe,
    staticfiles.version_static,
    staticfiles.collectstatic,
    staticfiles.compress,
    staticfiles.update_translations,
    formplayer.offline_build_formplayer,
    conditionally_stop_pillows_and_celery_during_migrate,
    db.create_kafka_topics,
    db.flip_es_aliases,
    staticfiles.update_manifest,
    release.clean_releases,
]


@task
def check_status():
    env.user = 'ansible'
    env.sudo_user = 'root'
    env.password = getpass('Enter the password for the ansbile user: ')

    execute(check_servers.ping)
    execute(check_servers.postgresql)
    execute(check_servers.elasticsearch)
    execute(check_servers.riakcs)


@task
def perform_system_checks():
    execute(check_servers.perform_system_checks, True)

    
@task
def deploy_airflow():
    execute(airflow.update_airflow)


def make_tasks_for_envs(available_envs):
    tasks = {}
    for env_name in available_envs:
        tasks[env_name] = task(alias=env_name)(functools.partial(_setup_env, env_name))
        tasks[env_name].__doc__ = get_environment(env_name).proxy_config['SITE_HOST']
    return tasks

# Automatically create a task for each environment
locals().update(make_tasks_for_envs(get_available_envs()))
