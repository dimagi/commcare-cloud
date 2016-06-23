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
import datetime
import json
import os
import posixpath
import sh
import time
import yaml
import re
from getpass import getpass
from distutils.util import strtobool
from github3 import login

from fabric import utils
from fabric.api import run, roles, execute, task, sudo, env, parallel, serial
from fabric.colors import blue, red, yellow, magenta
from fabric.context_managers import settings, cd, shell_env
from fabric.contrib import files, console
from fabric.operations import require
from const import (
    ROLES_ALL_SRC,
    ROLES_ALL_SERVICES,
    ROLES_CELERY,
    ROLES_PILLOWTOP,
    ROLES_DJANGO,
    ROLES_TOUCHFORMS,
    ROLES_STATIC,
    ROLES_SMS_QUEUE,
    ROLES_REMINDER_QUEUE,
    ROLES_PILLOW_RETRY_QUEUE,
    ROLES_DB_ONLY,
    RELEASE_RECORD,
    RSYNC_EXCLUDE,
)
from operations import (
    db,
    staticfiles,
    supervisor,
    formplayer,
)


if env.ssh_config_path and os.path.isfile(os.path.expanduser(env.ssh_config_path)):
    env.use_ssh_config = True

PROJECT_ROOT = os.path.dirname(__file__)
env.linewise = True
env.colorize_errors = True
env.captain_user = None
env.always_use_pty = False
env['sudo_prefix'] += '-H '

if not hasattr(env, 'code_branch'):
    print ("code_branch not specified, using 'master'. "
           "You can set it with '--set code_branch=<branch>'")
    env.code_branch = 'master'

env.roledefs = {
    'django_celery': [],
    'django_app': [],
    # for now combined with celery
    'django_pillowtop': [],
    'sms_queue': [],
    'reminder_queue': [],
    'pillow_retry_queue': [],
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
            provided_by=('staging', 'production', 'softlayer', 'zambia'))


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


@task
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


@roles(ROLES_ALL_SRC)
def setup_dirs():
    """
    create uploaded media, log, etc. directories (if needed) and make writable

    """
    sudo('mkdir -p %(log_dir)s' % env)
    sudo('chmod a+w %(log_dir)s' % env)
    sudo('mkdir -p %(services)s/supervisor' % env)


def load_env(env_name):
    def get_env_dict(path):
        if os.path.isfile(path):
            with open(path) as f:
                try:
                    return yaml.load(f)
                except Exception:
                    print 'Error in file {}'.format(path)
                    raise
        else:
            raise Exception("Environment file not found: {}".format(path))

    env_dict = get_env_dict(os.path.join(PROJECT_ROOT, 'environments.yml'))
    env.update(env_dict['base'])
    env.update(env_dict[env_name])


@task
def tsung():
    env.inventory = os.path.join(PROJECT_ROOT, 'inventory', 'tsung')
    load_env('tsung')
    execute(env_common)


@task
def swiss():
    env.inventory = os.path.join(PROJECT_ROOT, 'inventory', 'swiss')
    load_env('swiss')
    execute(env_common)


@task
def india():
    softlayer()


@task
def softlayer():
    env.inventory = os.path.join(PROJECT_ROOT, 'inventory', 'softlayer')
    load_env('softlayer')
    execute(env_common)


@task
def zambia():
    """Our production server in wv zambia."""
    env.inventory = os.path.join(PROJECT_ROOT, 'inventory', 'zambia')
    load_env('zambia')
    execute(env_common)


@task
def production():
    """www.commcarehq.org"""
    if env.code_branch != 'master':
        branch_message = (
            "Woah there bud! You're using branch {env.code_branch}. "
            "ARE YOU DOING SOMETHING EXCEPTIONAL THAT WARRANTS THIS?"
        ).format(env=env)
        if not console.confirm(branch_message, default=False):
            utils.abort('Action aborted.')

    load_env('production')
    env.inventory = os.path.join(PROJECT_ROOT, 'inventory', 'production')
    execute(env_common)


@task
def staging():
    """staging.commcarehq.org"""
    if env.code_branch == 'master':
        env.code_branch = 'autostaging'
        print ("using default branch of autostaging. you can override this "
               "with --set code_branch=<branch>")

    env.inventory = os.path.join(PROJECT_ROOT, 'inventory', 'staging')
    load_env('staging')
    execute(env_common)


def read_inventory_file(filename):
    """
    filename is a path to an ansible inventory file

    returns a mapping of group names ("webworker", "proxy", etc.)
    to lists of hosts (ip addresses)

    """
    from ansible.inventory import InventoryParser

    return {name: [host.name for host in group.get_hosts()]
            for name, group in InventoryParser(filename).groups.items()}


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

    env.deploy_metadata = DeployMetadata(env.code_branch, env.environment)
    _setup_path()

    proxy = servers['proxy']
    webworkers = servers['webworkers']
    postgresql = servers['postgresql']
    touchforms = servers['touchforms']
    elasticsearch = servers['elasticsearch']
    celery = servers['celery']
    rabbitmq = servers['rabbitmq']
    # if no server specified, just don't run pillowtop
    pillowtop = servers.get('pillowtop', [])

    deploy = servers.get('deploy', servers['postgresql'])[:1]

    env.roledefs = {
        'pg': postgresql,
        'rabbitmq': rabbitmq,
        'django_celery': celery,
        'sms_queue': celery,
        'reminder_queue': celery,
        'pillow_retry_queue': celery,
        'django_app': webworkers,
        'django_pillowtop': pillowtop,
        'formsplayer': touchforms,
        'staticfiles': proxy,
        'lb': [],
        # having deploy here makes it so that
        # we don't get prompted for a host or run deploy too many times
        'deploy': deploy,
        # fab complains if this doesn't exist
        'django_monolith': [],
    }
    env.roles = ['deploy']
    env.hosts = env.roledefs['deploy']
    env.supervisor_roles = ROLES_ALL_SRC


@task
def webworkers():
    env.supervisor_roles = ROLES_DJANGO


@task
def pillowtop():
    env.supervisor_roles = ROLES_PILLOWTOP


@task
@roles(ROLES_DB_ONLY)
def preindex_views():
    """
    Creates a new release that runs preindex_everything. Clones code from
    `current` release and updates it.
    """
    setup_release()
    db.preindex_views()


@roles(ROLES_ALL_SRC)
@parallel
def update_code(git_tag, use_current_release=False):
    # If not updating current release,  we are making a new release and thus have to do cloning
    # we should only ever not make a new release when doing a hotfix deploy
    if not use_current_release:
        if files.exists(env.code_current):
            with cd(env.code_current):
                submodules = sudo("git submodule | awk '{ print $2 }'").split()
        with cd(env.code_root):
            if files.exists(env.code_current):
                local_submodule_clone = []
                for submodule in submodules:
                    local_submodule_clone.append('-c')
                    local_submodule_clone.append(
                        'submodule.{submodule}.url={code_current}/.git/modules/{submodule}'.format(
                            submodule=submodule,
                            code_current=env.code_current
                        )
                    )

                sudo('git clone --recursive {} {}/.git {}'.format(
                    ' '.join(local_submodule_clone),
                    env.code_current,
                    env.code_root
                ))
                sudo('git remote set-url origin {}'.format(env.code_repo))
            else:
                sudo('git clone {} {}'.format(env.code_repo, env.code_root))

    with cd(env.code_root if not use_current_release else env.code_current):
        sudo('git remote prune origin')
        sudo('git fetch origin --tags -q')
        sudo('git checkout {}'.format(git_tag))
        sudo('git reset --hard {}'.format(git_tag))
        sudo('git submodule sync')
        sudo('git submodule update --init --recursive -q')
        # remove all untracked files, including submodules
        sudo("git clean -ffd")
        # remove all .pyc files in the project
        sudo("find . -name '*.pyc' -delete")


@roles(ROLES_DB_ONLY)
def mail_admins(subject, message):
    with cd(env.code_root):
        sudo((
            '%(virtualenv_root)s/bin/python manage.py '
            'mail_admins --subject "%(subject)s" "%(message)s" --slack'
        ) % {
            'virtualenv_root': env.virtualenv_root,
            'subject': subject,
            'message': message,
        })


@roles(ROLES_DB_ONLY)
def record_successful_deploy():
    with cd(env.code_current):
        env.deploy_metadata.tag_commit()
        sudo((
            '%(virtualenv_current)s/bin/python manage.py '
            'record_deploy_success --user "%(user)s" --environment '
            '"%(environment)s" --url %(url)s --mail_admins'
        ) % {
            'virtualenv_current': env.virtualenv_current,
            'user': env.captain_user or env.user,
            'environment': env.environment,
            'url': env.deploy_metadata.diff_url,
        })


@roles(ROLES_DB_ONLY)
def set_in_progress_flag(use_current_release=False):
    venv = env.virtualenv_root if not use_current_release else env.virtualenv_current
    with cd(env.code_root if not use_current_release else env.code_current):
        sudo('{}/bin/python manage.py deploy_in_progress'.format(venv))


@roles(ROLES_ALL_SRC)
@parallel
def record_successful_release():
    with cd(env.root):
        files.append(RELEASE_RECORD, str(env.code_root), use_sudo=True)


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
        execute(update_code, env.deploy_metadata.deploy_ref, True)
    except Exception:
        execute(mail_admins, "Deploy failed", "You had better check the logs.")
        # hopefully bring the server back to life
        silent_services_restart(use_current_release=True)
        raise
    else:
        silent_services_restart(use_current_release=True)
        execute(record_successful_deploy)


def _confirm_translated():
    if datetime.datetime.now().isoweekday() != 2 or env.environment != 'production':
        return True
    return console.confirm(
        "It's Tuesday, did you update the translations from transifex? "
        "Try running this handy script:\n./scripts/update-translations.sh\n"
    )


@task
def setup_release():
    deploy_ref = env.deploy_metadata.deploy_ref  # Make sure we have a valid commit
    _execute_with_timing(create_code_dir)
    _execute_with_timing(update_code, deploy_ref)
    _execute_with_timing(update_virtualenv)

    _execute_with_timing(copy_release_files)


def _deploy_without_asking():
    try:
        setup_release()

        _execute_with_timing(db.preindex_views)
        _execute_with_timing(db.ensure_preindex_completion)

        # handle static files
        _execute_with_timing(staticfiles.version_static)
        _execute_with_timing(staticfiles.bower_install)
        _execute_with_timing(staticfiles.npm_install)
        _execute_with_timing(staticfiles.collectstatic)
        _execute_with_timing(staticfiles.compress)

        supervisor.set_supervisor_config()

        _execute_with_timing(formplayer.build_formplayer)

        if all(execute(_migrations_exist).values()):
            _execute_with_timing(supervisor.stop_pillows)
            execute(set_in_progress_flag)
            _execute_with_timing(supervisor.stop_celery_tasks)
        _execute_with_timing(_migrate)

        _execute_with_timing(staticfiles.update_translations)
        _execute_with_timing(db.flip_es_aliases)

        # hard update of manifest.json since we're about to force restart
        # all services
        _execute_with_timing(staticfiles.update_manifest)
        _execute_with_timing(clean_releases)
    except PreindexNotFinished:
        mail_admins(
            " You can't deploy yet",
            ("Preindexing is taking a while, so hold tight "
             "and wait for an email saying it's done. "
             "Thank you for using AWESOME DEPLOY.")
        )
    except Exception:
        _execute_with_timing(
            mail_admins,
            "Deploy to {} failed".format(env.environment),
            "You had better check the logs."
        )
        # hopefully bring the server back to life
        silent_services_restart()
        raise
    else:
        _execute_with_timing(update_current)
        silent_services_restart()
        _execute_with_timing(record_successful_release)
        _execute_with_timing(record_successful_deploy)


@task
@roles(ROLES_ALL_SRC)
@parallel
def update_current(release=None):
    """
    Updates the current release to the one specified or to the code_root
    """
    if ((not release and not files.exists(env.code_root)) or
            (release and not files.exists(release))):
        utils.abort('About to update current to non-existant release')

    sudo('ln -nfs {} {}'.format(release or env.code_root, env.code_current))


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


@task
@roles(ROLES_ALL_SRC)
@parallel
def create_code_dir():
    sudo('mkdir -p {}'.format(env.code_root))


@parallel
@roles(ROLES_ALL_SRC)
def copy_localsettings():
    sudo('cp {}/localsettings.py {}/localsettings.py'.format(env.code_current, env.code_root))


@parallel
@roles(ROLES_TOUCHFORMS)
def copy_tf_localsettings():
    sudo(
        'cp {}/submodules/touchforms-src/touchforms/backend/localsettings.py '
        '{}/submodules/touchforms-src/touchforms/backend/localsettings.py'.format(
            env.code_current, env.code_root
        ))


@parallel
@roles(ROLES_TOUCHFORMS)
def copy_formplayer_properties():
    with settings(warn_only=True):
        sudo(
            'cp {}/submodules/formplayer/config/application.properties '
            '{}/submodules/formplayer/config'.format(
                env.code_current, env.code_root
            ))


@parallel
@roles(ROLES_ALL_SRC)
def copy_components():
    if files.exists('{}/bower_components'.format(env.code_current)):
        sudo('cp -r {}/bower_components {}/bower_components'.format(env.code_current, env.code_root))
    else:
        sudo('mkdir {}/bower_components'.format(env.code_root))


@parallel
@roles(ROLES_ALL_SRC)
def copy_node_modules():
    if files.exists('{}/node_modules'.format(env.code_current)):
        sudo('cp -r {}/node_modules {}/node_modules'.format(env.code_current, env.code_root))
    else:
        sudo('mkdir {}/node_modules'.format(env.code_root))


@parallel
@roles(ROLES_STATIC)
def copy_compressed_js_staticfiles():
    if files.exists('{}/staticfiles/CACHE/js'.format(env.code_current)):
        sudo('mkdir -p {}/staticfiles/CACHE/js'.format(env.code_root))
        sudo('cp -r {}/staticfiles/CACHE/js {}/staticfiles/CACHE/js'.format(env.code_current, env.code_root))


def copy_release_files():
    execute(copy_localsettings)
    execute(copy_tf_localsettings)
    execute(copy_formplayer_properties)
    execute(copy_components)
    execute(copy_node_modules)
    execute(copy_compressed_js_staticfiles)


@task
def rollback():
    """
    Rolls back the servers to the previous release if it exists and is same
    across servers.
    """
    number_of_releases = execute(get_number_of_releases)
    if not all(map(lambda n: n > 1, number_of_releases)):
        print red('Aborting because there are not enough previous releases.')
        exit()

    releases = execute(get_previous_release)

    unique_releases = set(releases.values())
    if len(unique_releases) != 1:
        print red('Aborting because not all hosts would rollback to same release')
        exit()

    unique_release = unique_releases.pop()

    if not unique_release:
        print red('Aborting because release path is empty. '
                  'This probably means there are no releases to rollback to.')
        exit()

    if not console.confirm('Do you wish to rollback to release: {}'.format(unique_release), default=False):
        print blue('Exiting.')
        exit()

    exists = execute(ensure_release_exists, unique_release)

    if all(exists.values()):
        print blue('Updating current and restarting services')
        execute(update_current, unique_release)
        silent_services_restart(use_current_release=True)
        execute(mark_last_release_unsuccessful)
    else:
        print red('Aborting because not all hosts have release')
        exit()


@roles(ROLES_ALL_SRC)
@parallel
def get_number_of_releases():
    with cd(env.root):
        return int(sudo("wc -l {} | awk '{{ print $1 }}'".format(RELEASE_RECORD)))


@roles(ROLES_ALL_SRC)
@parallel
def mark_last_release_unsuccessful():
    # Removes last line from RELEASE_RECORD file
    with cd(env.root):
        sudo("sed -i '$d' {}".format(RELEASE_RECORD))


@roles(ROLES_ALL_SRC)
@parallel
def ensure_release_exists(release):
    return files.exists(release)


@roles(ROLES_ALL_SRC)
@parallel
def get_previous_release():
    # Gets second to last line in RELEASES.txt
    with cd(env.root):
        return sudo('tail -2 {} | head -n 1'.format(RELEASE_RECORD))


@task
@roles(ROLES_ALL_SRC)
@parallel
def clean_releases(keep=3):
    """
    Cleans old and failed deploys from the ~/www/<environment>/releases/ directory
    """
    releases = sudo('ls {}'.format(env.releases)).split()
    current_release = os.path.basename(sudo('readlink {}'.format(env.code_current)))

    to_remove = []
    valid_releases = 0
    with cd(env.root):
        for index, release in enumerate(reversed(releases)):
            if (release == current_release or release == os.path.basename(env.code_root)):
                valid_releases += 1
            elif (files.contains(RELEASE_RECORD, release)):
                valid_releases += 1
                if valid_releases > keep:
                    to_remove.append(release)
            else:
                # cleans all releases that were not successful deploys
                to_remove.append(release)

    if len(to_remove) == len(releases):
        print red('Aborting clean_releases, about to remove every release')
        return

    if os.path.basename(env.code_root) in to_remove:
        print red('Aborting clean_releases, about to remove current release')
        return

    for release in to_remove:
        sudo('rm -rf {}/{}'.format(env.releases, release))


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
def awesome_deploy(confirm="yes"):
    """preindex and deploy if it completes quickly enough, otherwise abort"""
    _require_target()
    if strtobool(confirm) and (
        not _confirm_translated() or
        not console.confirm(
            'Are you sure you want to preindex and deploy to '
            '{env.environment}?'.format(env=env), default=False)
    ):
        utils.abort('Deployment aborted.')

    if datetime.datetime.now().isoweekday() == 5:
        warning_message = 'Friday'
    elif env.environment == 'zambia':
        warning_message = "Zambia"
    else:
        warning_message = ''

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


@roles(ROLES_ALL_SRC)
@parallel
def update_virtualenv():
    """
    update external dependencies on remote host

    assumes you've done a code update

    """
    _require_target()
    requirements = posixpath.join(env.code_root, 'requirements')

    # Optimization if we have current setup (i.e. not the first deploy)
    if files.exists(env.virtualenv_current):
        print 'Cloning virtual env'
        # There's a bug in virtualenv-clone that doesn't allow us to clone envs from symlinks
        current_virtualenv = sudo('readlink -f {}'.format(env.virtualenv_current))
        sudo("virtualenv-clone {} {}".format(current_virtualenv, env.virtualenv_root))

    with cd(env.code_root):
        cmd_prefix = 'export HOME=/home/%s && source %s/bin/activate && ' % (
            env.sudo_user, env.virtualenv_root)
        # uninstall requirements in uninstall-requirements.txt
        # but only the ones that are actually installed (checks pip freeze)
        sudo("%s bash scripts/uninstall-requirements.sh" % cmd_prefix,
             user=env.sudo_user)
        sudo('%s pip install --timeout 60 --quiet --requirement %s --requirement %s' % (
            cmd_prefix,
            posixpath.join(requirements, 'prod-requirements.txt'),
            posixpath.join(requirements, 'requirements.txt'),
        ))


@task
def supervisorctl(command):
    require('supervisor_roles',
            provided_by=('staging', 'production', 'softlayer', 'zambia'))

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
    execute(set_in_progress_flag, use_current_release)
    execute(supervisor.restart_all_except_webworkers)
    execute(supervisor.restart_webworkers)




@roles(ROLES_DB_ONLY)
def _migrate():
    """run south migration on remote environment"""
    _require_target()
    with cd(env.code_root):
        sudo('%(virtualenv_root)s/bin/python manage.py sync_finish_couchdb_hq' % env)
        sudo('%(virtualenv_root)s/bin/python manage.py migrate_multi --noinput' % env)


@roles(ROLES_DB_ONLY)
def _migrations_exist():
    """
    Check if there exists database migrations to run
    """
    _require_target()
    with cd(env.code_root):
        try:
            n_migrations = int(sudo(
                '%(virtualenv_root)s/bin/python manage.py migrate --list | grep "\[ ]" | wc -l' % env)
            )
        except Exception:
            # If we fail on this, return True to be safe. It's most likely cause we lost connection and
            # failed to return a value python could parse into an int
            return True
        return n_migrations > 0


@task
def set_supervisor_config():
    setup_release()
    supervisor.set_supervisor_config()


@task
def stop_pillows():
    execute(supervisor.stop_pillows, True)


@task
def stop_pillows():
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


def _execute_with_timing(fn, *args, **kwargs):
    start_time = datetime.datetime.utcnow()
    execute(fn, *args, **kwargs)
    if env.timing_log:
        with open(env.timing_log, 'a') as timing_log:
            duration = datetime.datetime.utcnow() - start_time
            timing_log.write('{}: {}\n'.format(fn.__name__, duration.seconds))


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


class PreindexNotFinished(Exception):
    pass
