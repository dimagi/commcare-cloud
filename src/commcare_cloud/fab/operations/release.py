from __future__ import absolute_import, print_function, unicode_literals

from fabric import utils
from fabric.api import env, parallel, roles, sudo
from fabric.context_managers import cd
from fabric.contrib import files

from ..const import RELEASE_RECORD, ROLES_ALL_SRC


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
