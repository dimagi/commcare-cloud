from fabric.api import roles, parallel, sudo, env
from fabric.context_managers import cd

from ..const import ROLES_STATIC, ROLES_DJANGO, ROLES_ALL_SRC


@roles(set(ROLES_STATIC + ROLES_DJANGO))
@parallel
def version_static():
    """
    Put refs on all static references to prevent stale browser cache hits when things change.
    This needs to be run on the WEB WORKER since the web worker governs the actual static
    reference.

    """

    cmd = 'resource_static'
    with cd(env.code_root):
        sudo(
            'rm -f tmp.sh resource_versions.py; {venv}/bin/python manage.py {cmd}'.format(
                venv=env.virtualenv_root, cmd=cmd
            ),
            user=env.sudo_user
        )


@parallel
@roles(ROLES_STATIC)
def bower_install():
    with cd(env.code_root):
        sudo('bower prune --production --config.interactive=false')
        sudo('bower update --production --config.interactive=false')


@parallel
@roles(ROLES_DJANGO)
def npm_install():
    with cd(env.code_root):
        sudo('npm prune --production')
        sudo('npm install --production')
        sudo('npm update --production')


@parallel
@roles(ROLES_STATIC)
def collectstatic(use_current_release=False):
    """Collect static after a code update"""
    venv = env.virtualenv_root if not use_current_release else env.virtualenv_current
    with cd(env.code_root if not use_current_release else env.code_current):
        sudo('{}/bin/python manage.py collectstatic --noinput -v 0'.format(venv))
        sudo('{}/bin/python manage.py fix_less_imports_collectstatic'.format(venv))
        sudo('{}/bin/python manage.py compilejsi18n'.format(venv))


@parallel
@roles(ROLES_STATIC)
def compress(use_current_release=False):
    """Run Django Compressor after a code update"""
    venv = env.virtualenv_root if not use_current_release else env.virtualenv_current
    with cd(env.code_root if not use_current_release else env.code_current):
        sudo('{}/bin/python manage.py compress --force -v 0'.format(venv))
        sudo('{}/bin/python manage.py purge_compressed_files'.format(venv))
    update_manifest(save=True, use_current_release=use_current_release)


@roles(ROLES_DJANGO)
@parallel
def update_manifest(save=False, soft=False, use_current_release=False):
    """
    Puts the manifest.json file with the references to the compressed files
    from the proxy machines to the web workers. This must be done on the WEB WORKER, since it
    governs the actual static reference.

    save=True saves the manifest.json file to redis, otherwise it grabs the
    manifest.json file from redis and inserts it into the staticfiles dir.
    """
    withpath = env.code_root if not use_current_release else env.code_current
    venv = env.virtualenv_root if not use_current_release else env.virtualenv_current

    args = ''
    if save:
        args = ' save'
    if soft:
        args = ' soft'
    cmd = 'update_manifest%s' % args
    with cd(withpath):
        sudo(
            '{venv}/bin/python manage.py {cmd}'.format(venv=venv, cmd=cmd),
            user=env.sudo_user
        )


@roles(ROLES_ALL_SRC)
@parallel
def update_translations():
    with cd(env.code_root):
        update_locale_command = '{virtualenv_root}/bin/python manage.py update_django_locales'.format(
            virtualenv_root=env.virtualenv_root,
        )
        update_translations_command = '{virtualenv_root}/bin/python manage.py compilemessages'.format(
            virtualenv_root=env.virtualenv_root,
        )
        sudo(update_locale_command)
        sudo(update_translations_command)
