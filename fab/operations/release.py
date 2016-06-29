import os
import posixpath

from fabric.api import roles, parallel, sudo, env
from fabric.colors import red
from fabric.context_managers import cd, settings
from fabric.contrib import files
from fabric import utils

from const import ROLES_ALL_SRC, ROLES_DB_ONLY, RELEASE_RECORD, ROLES_TOUCHFORMS, ROLES_STATIC


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


@roles(ROLES_ALL_SRC)
@parallel
def update_virtualenv():
    """
    update external dependencies on remote host

    assumes you've done a code update

    """
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


@roles(ROLES_ALL_SRC)
@parallel
def create_code_dir():
    sudo('mkdir -p {}'.format(env.code_root))


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
