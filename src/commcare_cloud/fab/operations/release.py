from __future__ import absolute_import
from __future__ import print_function
import os
import posixpath
from collections import namedtuple
from datetime import datetime, timedelta

from fabric.api import roles, parallel, sudo, env, run, local
from fabric.colors import red
from fabric.context_managers import cd
from fabric.contrib import files
from fabric.contrib.files import comment
from fabric.contrib.project import rsync_project
from fabric.operations import put
from fabric import utils, operations

from ..const import (
    OFFLINE_STAGING_DIR,
    ROLES_ALL_SRC,
    RELEASE_RECORD,
    ROLES_FORMPLAYER,
    ROLES_STATIC,
    ROLES_DEPLOY,
    ROLES_MANAGE,
    DATE_FMT,
    KEEP_UNTIL_PREFIX,
    FORMPLAYER_BUILD_DIR,
    ROLES_CONTROL)
from commcare_cloud.fab.utils import pip_install

GitConfig = namedtuple('GitConfig', 'key value')


def update_code(full_cluster=True):
    roles_to_use = _get_roles(full_cluster)

    @roles(roles_to_use)
    @parallel
    def update(git_tag, use_current_release=False):
        # If not updating current release,  we are making a new release and thus have to do cloning
        # we should only ever not make a new release when doing a hotfix deploy
        if not use_current_release:
            _update_code_from_previous_release()
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

    return update


@roles(ROLES_ALL_SRC)
@parallel
def create_offline_dir():
    run('mkdir -p {}'.format(env.offline_code_dir))


@roles(ROLES_CONTROL)
def sync_offline_dir():
    sync_offline_to_control()
    sync_offline_from_control()


def sync_offline_to_control():
    for sync_item in ['bower_components', 'node_modules', 'wheelhouse']:
        rsync_project(
            env.offline_code_dir,
            os.path.join(OFFLINE_STAGING_DIR, 'commcare-hq', sync_item),
            delete=True,
        )
    rsync_project(
        env.offline_code_dir,
        os.path.join(OFFLINE_STAGING_DIR, 'formplayer.jar'),
    )


def sync_offline_from_control():
    for host in _hosts_in_roles(ROLES_ALL_SRC, exclude_roles=ROLES_DEPLOY):
        run("rsync -rvz --exclude 'commcare-hq/*' {} {}".format(
            env.offline_code_dir,
            '{}@{}:{}'.format(env.user, host, env.offline_releases)
        ))


def _hosts_in_roles(roles, exclude_roles=None):
    hosts = set()
    for role, role_hosts in env.roledefs.items():
        if role in roles:
            hosts.update(role_hosts)

    if exclude_roles:
        hosts = hosts - _hosts_in_roles(exclude_roles)
    return hosts


@roles(ROLES_ALL_SRC)
@parallel
def update_code_offline():
    '''
    An online release usually clones from the previous release then tops
    off the new updates from the remote github. Since we can't access the remote
    Github, we do this:

        1. Clone the current release to the user's home directory
        2. Update that repo with any changes from the user's local copy of HQ (in offline-staging)
        3. Clone the user's home repo to the release that is being deployed (code_root)
    '''
    clone_current_release_to_home_directory()

    git_remote_url = 'ssh://{user}@{host}{code_dir}'.format(
        user=env.user,
        host=env.host,
        code_dir=os.path.join(env.offline_code_dir, 'commcare-hq')
    )

    local('cd {}/commcare-hq && git push {}/.git {}'.format(
        OFFLINE_STAGING_DIR,
        git_remote_url,
        env.deploy_metadata.deploy_ref,
    ))

    # Iterate through each submodule and push master
    local("cd {}/commcare-hq && git submodule foreach 'git push {}/$path/.git --all'".format(
        OFFLINE_STAGING_DIR,
        git_remote_url,
    ))

    clone_home_directory_to_release()
    with cd(env.code_root):
        sudo('git checkout `git rev-parse {}`'.format(env.deploy_metadata.deploy_ref))
        sudo('git reset --hard {}'.format(env.deploy_metadata.deploy_ref))
        sudo('git submodule update --init --recursive')
        # remove all untracked files, including submodules
        sudo("git clean -ffd")
        sudo('git remote set-url origin {}'.format(env.code_repo))
        sudo("find . -name '*.pyc' -delete")


def clone_current_release_to_home_directory():
    offline_hq_root = os.path.join(env.offline_code_dir, 'commcare-hq')
    if not files.exists(offline_hq_root):
        _clone_code_from_local_path(env.code_current, offline_hq_root, run_as_sudo=False)


def clone_home_directory_to_release():
    _clone_code_from_local_path(os.path.join(env.offline_code_dir, 'commcare-hq'), env.code_root, run_as_sudo=True)


@roles(ROLES_ALL_SRC)
@parallel
def update_bower_offline():
    sudo('cp -r {}/bower_components {}'.format(env.offline_code_dir, env.code_root))


@roles(ROLES_ALL_SRC)
@parallel
def update_npm_offline():
    sudo('cp -r {}/node_modules {}'.format(env.offline_code_dir, env.code_root))


def _upload_and_extract(zippath, strip_components=0):
    zipname = os.path.basename(zippath)
    put(zippath, env.offline_code_dir)

    run('tar -xzf {code_dir}/{zipname} -C {code_dir} --strip-components {components}'.format(
        code_dir=env.offline_code_dir,
        zipname=zipname,
        components=strip_components,
    ))


def _update_code_from_previous_release():
    if files.exists(env.code_current):
        _clone_code_from_local_path(env.code_current, env.code_root)
        with cd(env.code_root):
            sudo('git remote set-url origin {}'.format(env.code_repo))
    else:
        with cd(env.code_root):
            sudo('git clone {} {}'.format(env.code_repo, env.code_root))


def _get_git_submodule_urls(path):
    if files.exists(env.code_current):
        with cd(env.code_current):
            submodules = sudo("git submodule | awk '{ print $2 }'").split()

    local_submodule_config = []
    for submodule in submodules:
        local_submodule_config.append(
            GitConfig(
                key='submodule.{submodule}.url'.format(submodule=submodule),
                value='{path}/.git/modules/{submodule}'.format(
                    path=path,
                    submodule=submodule,
                )
            )
        )
    return local_submodule_config


def _clone_code_from_local_path(from_path, to_path, run_as_sudo=True):
    cmd_fn = sudo if run_as_sudo else run
    submodule_configs = _get_git_submodule_urls(from_path)
    git_config_cmd = []
    for submodule_config in submodule_configs:
        git_config_cmd.append('git config {} {}'.format(submodule_config.key, submodule_config.value))

    with cd(from_path):
        cmd_fn('git clone {}/.git {}'.format(
            from_path,
            to_path
        ))

    with cd(to_path):
        cmd_fn('git config receive.denyCurrentBranch updateInstead')
        cmd_fn(' && '.join(git_config_cmd))
        cmd_fn('git submodule update --init --recursive')


def _clone_virtual_env(virtualenv_current, virtualenv_root):
    print('Cloning virtual env')
    # There's a bug in virtualenv-clone that doesn't allow us to clone envs from symlinks
    current_virtualenv = sudo('readlink -f {}'.format(virtualenv_current))
    sudo("virtualenv-clone {} {}".format(current_virtualenv, virtualenv_root))


@roles(ROLES_ALL_SRC)
@parallel
def clone_virtualenv():
    _clone_virtual_env(env.py2_virtualenv_current, env.py2_virtualenv_root)
    if env.py3_include_venv:
        _clone_virtual_env(env.py3_virtualenv_current, env.py3_virtualenv_root)


def update_virtualenv(full_cluster=True):
    """
    update external dependencies on remote host

    assumes you've done a code update

    """
    roles_to_use = _get_roles(full_cluster)

    @roles(roles_to_use)
    @parallel
    def update():
        def _update_virtualenv(virtualenv_current, virtualenv_root, requirements):
            # Optimization if we have current setup (i.e. not the first deploy)
            if files.exists(virtualenv_current):
                _clone_virtual_env(virtualenv_current, virtualenv_root)

            with cd(env.code_root):
                cmd_prefix = 'export HOME=/home/%s && source %s/bin/activate && ' % (
                    env.sudo_user, virtualenv_root)
                # uninstall requirements in uninstall-requirements.txt
                # but only the ones that are actually installed (checks pip freeze)
                sudo("%s bash scripts/uninstall-requirements.sh" % cmd_prefix,
                     user=env.sudo_user)
                pip_install(cmd_prefix, timeout=60, quiet=True, proxy=env.http_proxy, requirements=[
                    posixpath.join(requirements, 'prod-requirements.txt'),
                    posixpath.join(requirements, 'requirements.txt'),
                ])

        _update_virtualenv(
            env.py2_virtualenv_current, env.py2_virtualenv_root,
            posixpath.join(env.code_root, 'requirements')
        )
        if env.py3_include_venv:
            _update_virtualenv(
                env.py3_virtualenv_current, env.py3_virtualenv_root,
                posixpath.join(env.code_root, 'requirements-python3_6')
            )

    return update

def create_code_dir(full_cluster=True):
    roles_to_use = _get_roles(full_cluster)

    @roles(roles_to_use)
    @parallel
    def create():
        sudo('mkdir -p {}'.format(env.code_root))

    return create

@roles(ROLES_DEPLOY)
def kill_stale_celery_workers(delay=0):
    with cd(env.code_current):
        sudo(
            'echo "{}/bin/python manage.py '
            'kill_stale_celery_workers" '
            '| at now + {} minutes'.format(env.virtualenv_current, delay)
        )


@roles(ROLES_DEPLOY)
def record_successful_deploy():
    start_time = datetime.strptime(env.deploy_metadata.timestamp, DATE_FMT)
    delta = datetime.utcnow() - start_time
    with cd(env.code_current):
        env.deploy_metadata.tag_commit()
        sudo((
            '%(virtualenv_current)s/bin/python manage.py '
            'record_deploy_success --user "%(user)s" --environment '
            '"%(environment)s" --url %(url)s --minutes %(minutes)s --mail_admins'
        ) % {
            'virtualenv_current': env.virtualenv_current,
            'user': env.user,
            'environment': env.deploy_env,
            'url': env.deploy_metadata.diff_url,
            'minutes': str(int(delta.total_seconds() // 60))
        })


@roles(ROLES_ALL_SRC)
@parallel
def record_successful_release():
    with cd(env.root):
        files.append(RELEASE_RECORD, str(env.code_root), use_sudo=True)


#TODO make this a nicer task
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


@roles(ROLES_ALL_SRC)
@parallel
def mark_last_release_unsuccessful():
    # Removes last line from RELEASE_RECORD file
    with cd(env.root):
        sudo("sed -i '$d' {}".format(RELEASE_RECORD))


def git_gc_current():
    with cd(env.code_current):
        sudo('echo "git gc" | at -t `date -d "5 seconds" +%m%d%H%M.%S`')
        sudo('echo "git submodule foreach \'git gc\'" | at -t `date -d "5 seconds" +%m%d%H%M.%S`')


@roles(ROLES_ALL_SRC)
@parallel
def clean_releases(keep=3):
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
            elif files.exists(os.path.join(env.releases, release, KEEP_UNTIL_PREFIX + '*')):
                # This has a KEEP_UNTIL file, so let's not delete until time is up
                with cd(os.path.join(env.releases, release)):
                    filepath = sudo('find . -name {}*'.format(KEEP_UNTIL_PREFIX))
                filename = os.path.basename(filepath)
                _, date_to_delete_string = filename.split(KEEP_UNTIL_PREFIX)
                date_to_delete = datetime.strptime(date_to_delete_string, DATE_FMT)
                if date_to_delete < datetime.utcnow():
                    to_remove.append(release)
            else:
                # cleans all releases that were not successful deploys
                to_remove.append(release)

    if len(to_remove) == len(releases):
        print(red('Aborting clean_releases, about to remove every release'))
        return

    if os.path.basename(env.code_root) in to_remove:
        print(red('Aborting clean_releases, about to remove current release'))
        return

    for release in to_remove:
        sudo('rm -rf {}/{}'.format(env.releases, release))

    # as part of the clean up step, run gc in the 'current' directory
    git_gc_current()


def copy_localsettings(full_cluster=True):
    roles_to_use = _get_roles(full_cluster)

    @parallel
    @roles(roles_to_use)
    def copy():
        sudo('cp {}/localsettings.py {}/localsettings.py'.format(env.code_current, env.code_root))

    return copy


@parallel
@roles(ROLES_FORMPLAYER)
def copy_formplayer_properties():
    sudo(
        'cp -r {} {}'.format(
            os.path.join(env.code_current, FORMPLAYER_BUILD_DIR),
            os.path.join(env.code_root, FORMPLAYER_BUILD_DIR)
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
        sudo('mkdir -p {}/staticfiles/CACHE'.format(env.code_root))
        sudo('cp -r {}/staticfiles/CACHE/js {}/staticfiles/CACHE/js'.format(env.code_current, env.code_root))


@roles(ROLES_ALL_SRC)
@parallel
def get_previous_release():
    # Gets second to last line in RELEASES.txt
    with cd(env.root):
        return sudo('tail -2 {} | head -n 1'.format(RELEASE_RECORD))


@roles(ROLES_ALL_SRC)
@parallel
def get_number_of_releases():
    with cd(env.root):
        return int(sudo("wc -l {} | awk '{{ print $1 }}'".format(RELEASE_RECORD)))


@roles(ROLES_ALL_SRC)
@parallel
def ensure_release_exists(release):
    return files.exists(release)


def mark_keep_until(full_cluster=True):
    roles_to_use = _get_roles(full_cluster)

    @roles(roles_to_use)
    @parallel
    def mark(keep_days):
        until_date = (datetime.utcnow() + timedelta(days=keep_days)).strftime(DATE_FMT)
        with cd(env.code_root):
            sudo('touch {}{}'.format(KEEP_UNTIL_PREFIX, until_date))

    return mark


@roles(ROLES_ALL_SRC)
@parallel
def apply_patch(filepath):
    destination = '/home/{}/{}.patch'.format(env.user, env.deploy_metadata.timestamp)
    operations.put(
        filepath,
        destination,
    )

    current_dir = sudo('readlink -f {}'.format(env.code_current))
    sudo('git apply --unsafe-paths {} --directory={}'.format(destination, current_dir))


@roles(ROLES_ALL_SRC)
@parallel
def reverse_patch(filepath):
    destination = '/home/{}/{}.patch'.format(env.user, env.deploy_metadata.timestamp)
    operations.put(
        filepath,
        destination,
    )

    current_dir = sudo('readlink -f {}'.format(env.code_current))
    sudo('git apply -R --unsafe-paths {} --directory={}'.format(destination, current_dir))


def _get_roles(full_cluster):
    return ROLES_ALL_SRC if full_cluster else ROLES_MANAGE
