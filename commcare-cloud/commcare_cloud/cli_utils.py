import re
import subprocess
from clint.textui import puts, colored
from commcare_cloud.environment import ANSIBLE_DIR


def ask(message, strict=False, quiet=False):
    if quiet:
        return True
    yesno = 'YES/NO' if strict else 'y/N'
    negatives = ('NO', 'N', 'n', 'no', '')
    affirmatives = ('YES',) if strict else ('y', 'Y', 'yes')
    acceptable_options = affirmatives + negatives

    r = input('{} [{}]'.format(message, yesno))
    while r not in acceptable_options:
        r = input('{} or {}? '.format(*yesno.split('/')))
    return r in affirmatives


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


def git_branch():
    # https://stackoverflow.com/a/19585361/10840
    return subprocess.check_output(
        "git status | head -1", cwd=ANSIBLE_DIR, shell=True
    ).strip().split()[-1]


def check_branch(args):
    branch = git_branch()
    if args.branch != branch:
        if branch != 'master':
            puts(colored.red("You are not on branch master. To deploy anyway, use --branch={}".format(branch)))
        else:
            puts(colored.red("You are on branch master. To deploy, remove --branch={}".format(args.branch)))
        exit(-1)
