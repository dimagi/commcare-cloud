from __future__ import absolute_import, print_function, unicode_literals

import os
from datetime import datetime, timedelta

from fabric import utils
from fabric.api import env, parallel, roles, sudo
from fabric.colors import red
from fabric.context_managers import cd
from fabric.contrib import files

from ..const import (
    DATE_FMT,
    KEEP_UNTIL_PREFIX,
    RELEASE_RECORD,
    ROLES_ALL_SRC,
    ROLES_MANAGE,
)


@roles(ROLES_ALL_SRC)
@parallel
def record_successful_release():
    with cd(env.root):
        files.append(RELEASE_RECORD, str(env.code_root), use_sudo=True)


@roles(ROLES_ALL_SRC)
@parallel
def update_current(release=None):
    """
    Updates the current release to the one specified or to the code_root
    """
    if ((not release and not files.exists(env.code_root, use_sudo=True)) or
            (release and not files.exists(release, use_sudo=True))):
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
            if release == 'git_mirrors':
                continue  # do not delete reference repositories
            if release == current_release or release == os.path.basename(env.code_root):
                valid_releases += 1
            elif files.contains(RELEASE_RECORD, release, use_sudo=True, shell=True):
                valid_releases += 1
                if valid_releases > keep:
                    to_remove.append(release)
            elif files.exists(os.path.join(env.releases, release, KEEP_UNTIL_PREFIX + '*'), use_sudo=True):
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

    if valid_releases < keep:
        print(red('\n\nAborting clean_releases, {}/{} valid '
                  'releases were found\n\n'.format(valid_releases, keep)))
        return

    for release in to_remove:
        sudo('rm -rf {}/{}'.format(env.releases, release))

    # as part of the clean up step, run gc in the 'current' directory
    git_gc_current()


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
    return files.exists(release, use_sudo=True)


def mark_keep_until(full_cluster=True):
    roles_to_use = _get_roles(full_cluster)

    @roles(roles_to_use)
    @parallel
    def mark(keep_days):
        until_date = (datetime.utcnow() + timedelta(days=keep_days)).strftime(DATE_FMT)
        with cd(env.code_root):
            sudo('touch {}{}'.format(KEEP_UNTIL_PREFIX, until_date))

    return mark
