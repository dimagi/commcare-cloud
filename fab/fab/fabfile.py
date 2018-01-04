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
import os
import posixpath
from getpass import getpass

import yaml
import pipes
import pytz
from distutils.util import strtobool

from fabric import utils
from fabric.api import run, roles, execute, task, sudo, env, parallel, local
from fabric.colors import blue, red, magenta
from fabric.context_managers import cd
from fabric.contrib import files, console
from fabric.decorators import runs_once
from fabric.operations import require
from .const import (
    ROLES_ALL_SRC,
    ROLES_ALL_SERVICES,
    ROLES_CELERY,
    ROLES_PILLOWTOP,
    ROLES_DJANGO,
    ROLES_STATIC,
    ROLES_SMS_QUEUE,
    ROLES_REMINDER_QUEUE,
    ROLES_PILLOW_RETRY_QUEUE,
    ROLES_DB_ONLY,
    ROLES_DEPLOY,
    RELEASE_RECORD,
    RSYNC_EXCLUDE,
    PROJECT_ROOT,
    REPO_BASE)
from .exceptions import PreindexNotFinished
from .operations import (
    db,
    staticfiles,
    supervisor,
    formplayer,
    release,
    offline as offline_ops,
)
from .utils import (
    DeployMetadata,
    cache_deploy_state,
    clear_cached_deploy,
    execute_with_timing,
    read_inventory_file,
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
env.captain_user = None
env.email_enabled = True
env.always_use_pty = False
env['sudo_prefix'] += '-H '

if not hasattr(env, 'code_branch'):
    print ("code_branch not specified, using 'master'. "
           "You can set it with '--set code_branch=<branch>'")
    env.code_branch = 'master'


if not hasattr(env, 'force'):
    env.force = False  # --set force=true to override blocking warnings (e.g. stale pillow checkpoints)


env.roledefs = {
    'django_celery': [],
    'django_app': [],
    # for now combined with celery
    'django_pillowtop': [],
    'sms_queue': [],
    'reminder_queue': [],
    'pillow_retry_queue': [],
    'submission_reprocessing_queue': [],
    # 'django_celery, 'django_app', and 'django_pillowtop' all in one
    # use this ONLY for single server config,
    # otherwise deploy() will run multiple times in parallel causing issues
    'django_monolith': [],

    'formsplayer': [],
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
    require('root', 'code_root', 'hosts', 'environment',
            provided_by=('staging', 'production', 'softlayer'))


def _setup_path():
    # using posixpath to ensure unix style slashes.
    # See bug-ticket: http://code.fabfile.org/attachments/61/posixpath.patch
    env.root = posixpath.join(env.home, 'www', env.environment)
    env.log_dir = posixpath.join(env.home, 'www', env.environment, 'log')
    env.releases = posixpath.join(env.root, 'releases')
    env.code_current = posixpath.join(env.root, 'current')
    env.code_root = posixpath.join(env.releases, env.deploy_metadata.timestamp)
    env.project_root = posixpath.join(env.code_root, env.project)
    env.project_media = posixpath.join(env.code_root, 'media')
    env.virtualenv_current = posixpath.join(env.code_current, 'python_env')
    env.virtualenv_root = posixpath.join(env.code_root, 'python_env')
    env.services = posixpath.join(env.code_root, 'services')
    env.jython_home = '/usr/local/lib/jython'
    env.db = '%s_%s' % (env.project, env.environment)
    env.offline_releases = posixpath.join('/home/{}/releases'.format(env.user))
    env.offline_code_dir = posixpath.join('{}/{}'.format(env.offline_releases, 'offline'))


def load_env(env_name):
    def get_env_dict(path):
        if os.path.isfile(path):
            with open(path) as f:
                try:
                    return yaml.load(f)
                except Exception:
                    print('Error in file {}'.format(path))
                    raise
        else:
            raise Exception("Environment file not found: {}".format(path))

    env_dict = get_env_dict(os.path.join(REPO_BASE, 'environments', env_name, 'app-processes.yml'))
    base_dict = get_env_dict(os.path.join(REPO_BASE, 'environmental-defaults', 'app-processes.yml'))
    env.update(base_dict)
    env.update(env_dict)


@task
def swiss():
    """swiss.commcarehq.org"""
    _setup_env('swiss', force=True)


@task(alias='india')
def softlayer():
    """india.commcarehq.org"""
    _setup_env('softlayer')


@task
def icds():
    """www.icds-cas.gov.in"""
    _confirm_environment_time('icds', 'Asia/Kolkata')
    _setup_env('icds')


@task(alias='icds-new')
def icds_new():
    """www.icds-cas.gov.in"""
    _confirm_environment_time('icds-new', 'Asia/Kolkata')
    _setup_env('icds-new')
    env.email_enabled = False


@task
def enikshay():
    """enikshay.in"""
    _confirm_environment_time('enikshay', 'Asia/Kolkata')
    _setup_env('enikshay', force=True)


@task
def pna():
    """commcare.pna.sn"""
    _setup_env('pna', force=True)


@task
def l10k():
    """l10k.commcare.org"""
    _setup_env('l10k', force=True)


@task
def production():
    """www.commcarehq.org"""
    _setup_env('production')


@task
def staging():
    """staging.commcarehq.org"""
    _setup_env('staging', force=True, default_branch='autostaging')


def _setup_env(env_name, force=False, default_branch=None):
    _confirm_branch(default_branch)
    env.env_name = env_name
    env.force = force  # don't worry about kafka checkpoints if True
    env.inventory = os.path.join(REPO_BASE, 'environments', env_name, 'inventory.ini')
    load_env(env_name)
    execute(env_common)


def _confirm_branch(default_branch=None):
    if env.code_branch == 'master':
        if default_branch:
            env.code_branch = default_branch
            print ("using default branch of {}. you can override this "
                   "with --set code_branch=<branch>".format(default_branch))
    else:
        branch_message = (
            "Woah there bud! You're using branch {env.code_branch}. "
            "ARE YOU DOING SOMETHING EXCEPTIONAL THAT WARRANTS THIS?"
        ).format(env=env)
        if not console.confirm(branch_message, default=False):
            utils.abort('Action aborted.')


def _confirm_environment_time(env_name, env_tz):
    env_hours_start_end = {
        'enikshay': (2, 7),  # call center is offline 2am-8am IST
        'icds': (0, 7),
        'icds-new': (0, 7),
    }
    hour_start, hour_end = env_hours_start_end[env_name]
    d = datetime.datetime.now(pytz.timezone(env_tz))
    if hour_start <= d.hour < hour_end:
        return

    message = (
        "Woah there bud! You're deploying '%s' during the day. "
        "The current local time is %s.\n"
        "ARE YOU DOING SOMETHING EXCEPTIONAL THAT WARRANTS THIS?"
    ) % (env_name, d.strftime("%-I:%M%p on %h. %d %Z"))
    if not console.confirm(message, default=False):
        utils.abort('Action aborted.')


@task
def development():
    """
    Must pass in the 'inventory' env variable,
    which is the path to an ansible inventory file
    and an 'environment' env variable,
    which is the name of the directory to be used under /home/cchq/www/

    Example command:

        fab development awesome_deploy \
        --set inventory=/path/to/commcarehq-ansible/ansible/inventories/development,environment=dev

    """
    load_env('development')
    execute(env_common)


def env_common():
    require('inventory', 'environment')
    servers = read_inventory_file(env.inventory)
    print(servers)

    env.is_monolith = len(set(servers['all']) - set(servers['control'])) < 2

    env.deploy_metadata = DeployMetadata(env.code_branch, env.environment)
    _setup_path()

    all = servers['all']
    print(all)
    proxy = servers['proxy']
    webworkers = servers['webworkers']
    riakcs = servers.get('riakcs', [])
    postgresql = servers['postgresql']
    pg_standby = servers.get('pg_standby', [])
    touchforms = servers['touchforms']
    formplayer = servers['formplayer']
    elasticsearch = servers['elasticsearch']
    celery = servers['celery']
    rabbitmq = servers['rabbitmq']
    # if no server specified, just don't run pillowtop
    pillowtop = servers.get('pillowtop', [])

    deploy = servers.get('deploy', servers['postgresql'])[:1]

    env.roledefs = {
        'all': all,
        'pg': postgresql,
        'pgstandby': pg_standby,
        'elasticsearch': elasticsearch,
        'riakcs': riakcs,
        'rabbitmq': rabbitmq,
        'django_celery': celery,
        'sms_queue': celery,
        'reminder_queue': celery,
        'pillow_retry_queue': celery,
        'submission_reprocessing_queue': celery,
        'django_app': webworkers,
        'django_pillowtop': pillowtop,
        'formsplayer': touchforms,
        'formplayer': formplayer,
        'staticfiles': proxy,
        'lb': [],
        # having deploy here makes it so that
        # we don't get prompted for a host or run deploy too many times
        'deploy': deploy,
        # fab complains if this doesn't exist
        'django_monolith': [],
        'control': servers.get('control')[:1]
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
    setup_release()
    db.preindex_views()


@roles(ROLES_DEPLOY)
def mail_admins(subject, message, use_current_release=False):
    code_dir = env.code_current if use_current_release else env.code_root
    virtualenv_dir = env.virtualenv_current if use_current_release else env.virtualenv_root
    with cd(code_dir):
        sudo((
            '%(virtualenv_dir)s/bin/python manage.py '
            'mail_admins --subject %(subject)s %(message)s --slack --environment %(environment)s'
        ) % {
            'virtualenv_dir': virtualenv_dir,
            'subject': pipes.quote(subject),
            'message': pipes.quote(message),
            'environment': pipes.quote(env.environment),
        })


@task
def hotfix_deploy():
    """
    deploy ONLY the code with no extra cleanup or syncing

    for small python-only hotfixes

    """
    if not console.confirm('Are you sure you want to deploy to {env.environment}?'.format(env=env), default=False) or \
       not console.confirm('Did you run "fab {env.environment} preindex_views"? '.format(env=env), default=False) or \
       not console.confirm('HEY!!!! YOU ARE ONLY DEPLOYING CODE. THIS IS NOT A NORMAL DEPLOY. COOL???', default=False):
        utils.abort('Deployment aborted.')

    _require_target()
    run('echo ping!')  # workaround for delayed console response
    try:
        execute(release.update_code, env.deploy_metadata.deploy_ref, True)
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
    if datetime.datetime.now().isoweekday() != 2 or env.environment != 'production':
        return True
    return console.confirm(
        "It's Tuesday, did you update the translations from transifex? "
        "Try running this handy script:\n./scripts/update-translations.sh\n"
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


@task
def setup_release(keep_days=0):
    """
    Setup a release in the releases directory with the most recent code.
    Useful for running management commands. These releases will automatically
    be cleaned up at the finish of each deploy. To ensure that a release will
    last past a deploy use the `keep_days` param.

    :param keep_days: The number of days to keep this release before it will be purged

    Example:
    fab <env> setup_release:keep_days=10  # Makes a new release that will last for 10 days
    """
    try:
        keep_days = int(keep_days)
    except ValueError:
        print(red("Unable to parse '{}' into an integer".format(keep_days)))
        exit()

    deploy_ref = env.deploy_metadata.deploy_ref  # Make sure we have a valid commit
    execute_with_timing(release.create_code_dir)
    execute_with_timing(release.update_code, deploy_ref)
    execute_with_timing(release.update_virtualenv)

    execute_with_timing(copy_release_files)

    if keep_days > 0:
        execute_with_timing(release.mark_keep_until, keep_days)

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
    execute_with_timing(
        mail_admins,
        "{user} has initiated a deploy to {environment}.".format(
            user=env.user,
            environment=env.environment,
        ),
        ''
    )


def announce_formplayer_deploy_start():
    execute_with_timing(
        mail_admins,
        "{user} has initiated a formplayer deploy to {environment}.".format(
            user=env.user,
            environment=env.environment,
        ),
        '',
        use_current_release=True,
    )


def _deploy_without_asking():
    if env.offline:
        commands = OFFLINE_DEPLOY_COMMANDS
    else:
        commands = ONLINE_DEPLOY_COMMANDS

    try:
        for index, command in enumerate(commands):
            deploy_checkpoint(index, command.__name__, execute_with_timing, command)
    except PreindexNotFinished:
        mail_admins(
            " You can't deploy to {} yet. There's a preindex in process.".format(env.environment),
            ("Preindexing is taking a while, so hold tight "
             "and wait for an email saying it's done. "
             "Thank you for using AWESOME DEPLOY.")
        )
    except Exception:
        execute_with_timing(
            mail_admins,
            "Deploy to {environment} failed. Try resuming with "
            "fab {environment} deploy:resume=yes.".format(environment=env.environment),
            traceback_string()
        )
        # hopefully bring the server back to life
        silent_services_restart()
        raise
    else:
        execute_with_timing(release.update_current)
        silent_services_restart()
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
    message = 'Are you sure you want to unlink the current release of {env.environment}?'.format(env=env)

    if not console.confirm(message, default=False):
        utils.abort('Deployment aborted.')

    if files.exists(env.code_current):
        sudo('unlink {}'.format(env.code_current))


def copy_release_files():
    execute(release.copy_localsettings)
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
def awesome_deploy(confirm="yes", resume='no', offline='no'):
    """Preindex and deploy if it completes quickly enough, otherwise abort
    fab <env> deploy:confirm=no  # do not confirm
    fab <env> deploy:resume=yes  # resume from previous deploy
    fab <env> deploy:offline=yes  # offline deploy
    """
    _require_target()
    if strtobool(confirm) and (
        not _confirm_translated() or
        not console.confirm(
            'Are you sure you want to preindex and deploy to '
            '{env.environment}?'.format(env=env), default=False)
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

    _deploy_without_asking()


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
                           '{env.environment}?'.format(env=env), default=False):
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
def set_supervisor_config():
    setup_release()
    execute_with_timing(supervisor.set_supervisor_config)


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
    setup_release()
    mvp_pillows = [
        'MVPFormIndicatorPillow',
        'MVPCaseIndicatorPillow',
    ]
    for pillow in mvp_pillows:
        reset_pillow(pillow)


@roles(ROLES_PILLOWTOP)
def reset_pillow(pillow):
    _require_target()
    prefix = 'commcare-hq-{}-pillowtop'.format(env.environment)
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
    setup_release,
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
    supervisor.set_supervisor_config,
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
    supervisor.set_supervisor_config,
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
