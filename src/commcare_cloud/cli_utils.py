from __future__ import absolute_import, print_function, unicode_literals

import re
import subprocess
import sys
from io import open

from clint.textui import puts
from six.moves import input, shlex_quote

from commcare_cloud.colors import color_code, color_error

from .environment.paths import ANSIBLE_DIR


def ask(message, strict=False, quiet=False):
    if quiet:
        return True
    yesno = 'YES/NO' if strict else 'y/N'
    negatives = ('NO', 'N', 'n', 'no', '')
    affirmatives = ('YES',) if strict else ('y', 'Y', 'yes')
    acceptable_options = affirmatives + negatives

    response = ask_option(message, yesno.split('/'), acceptable_options)
    return response in affirmatives


def ask_option(message, options, acceptable_responses=None):
    options_display = '/'.join(options)
    acceptable_responses = acceptable_responses or options
    r = input('{} [{}]'.format(message, options_display))
    while r not in acceptable_responses:
        r = input('Please enter one of {} :'.format(', '.join(options)))
    return r


def has_arg(unknown_args, short_form, long_form):
    """
    check whether a conceptual arg is present in a list of command line tokens

    :param unknown_args: list of command line tokens
    :param short_form: dash followed by single letter, e.g. '-f'
    :param long_form: double dash followed by work, e.g. '--forks'
    :return: boolean
    """

    assert re.match(r'^-[a-zA-Z0-9]$', short_form)
    assert re.match(r'^--\w+$', long_form)
    if long_form in unknown_args:
        return True
    for arg in unknown_args:
        if arg.startswith(short_form):
            return True
    return False


def has_local_connection_arg(args):
    return ("--connection=local" in args or ('-c' in args
            and 'local' in args and args.index('-c') + 1 == args.index('local')))


def git_branch():
    # https://stackoverflow.com/a/19585361/10840
    status = git("status")
    return status.splitlines()[0].strip().split()[-1] if status else status


def require_clean_working_tree(abort=sys.exit):
    # http://stackoverflow.com/a/3879077/10840
    git("update-index", "-q", "--ignore-submodules", "--refresh")

    # Disallow unstaged changes in the working tree
    try:
        git("diff-files", "--quiet", "--ignore-submodules", "--")
    except subprocess.CalledProcessError:
        abort("Aborting. You have unstaged changes.")

    # Disallow uncommitted changes in the index
    try:
        git("diff-index", "--cached", "--quiet", "HEAD", "--ignore-submodules", "--")
    except subprocess.CalledProcessError:
        abort("Aborting. You have uncommitted changes.")


def git(*args):
    try:
        with open('/dev/null', 'w', encoding='utf-8') as devnull:
            return subprocess.check_output(
                ["git"] + list(args),
                cwd=ANSIBLE_DIR,
                stderr=devnull,
                universal_newlines=True,
            )
    except subprocess.CalledProcessError as e:
        if e.returncode == 128:
            # We are not in a git repo; most likely pip installed
            return None
        raise


def check_branch(args):
    branch = git_branch()
    if branch is None:
        # not in a git repo
        if args.branch != 'master':
            puts(color_error("You are not in a git repo. To deploy, remove --branch={}".format(branch)))
            exit(-1)
    elif args.branch != branch:
        puts(color_error("You are not currently on the branch specified with the --branch tag. To deploy on "
                         "this branch, use --branch={}, otherwise, change branches".format(branch)))
        exit(-1)
    elif branch == 'master' and not any(a.startswith("--branch") for a in sys.argv):
        require_clean_working_tree()
        local_rev = git("rev-parse", branch).strip()
        remote = "https://github.com/dimagi/commcare-cloud.git"
        remote_rev = git("ls-remote", remote, "refs/heads/master").split(maxsplit=1)[0]
        if local_rev != remote_rev:
            print("Your local 'master' branch has diverged from upstream")
            print(f"local:  {local_rev}")
            print(f"remote: {remote_rev}")
            print("")
            print("Run 'git pull' to get the latest code, then try again.")
            print("Create a pull request if you have new commits to contribute.")
            print("Or add --branch=master to use your local branch (not recommended).")
            exit(-1)


def print_command(command):
    """
    commcare-cloud commands by convention print the underlying command they execute

    Use this function to do so
    """
    if isinstance(command, (list, tuple)):
        command = ' '.join(shlex_quote(arg) for arg in command)
    print(color_code(command), file=sys.stderr)
