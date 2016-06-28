from fabric.api import roles, parallel, sudo, env
from fabric.context_managers import cd
from fabric.contrib import files

from const import ROLES_ALL_SRC


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
