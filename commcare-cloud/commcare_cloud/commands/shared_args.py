import os


def arg_inventory_group(parser):
    parser.add_argument('inventory_group', help=(
        "The inventory group to run the command on. Use 'all' for all hosts."
    ))


def arg_skip_check(parser):
    parser.add_argument('--skip-check', action='store_true', default=False, help=(
        "skip the default of viewing --check output first"
    ))


def arg_quiet(parser):
    parser.add_argument('--quiet', action='store_true', default=False, help=(
        "skip all user prompts and proceed as if answered in the affirmative"
    ))


def arg_branch(parser):
    parser.add_argument('--branch', default='master', help=(
        "the name of the commcare-cloud git branch to run against, if not master"
    ))


def arg_stdout_callback(parser):
    default = os.environ.get('ANSIBLE_STDOUT_CALLBACK') or 'default'
    parser.add_argument(
        '--output', dest='stdout_callback', default=default, choices=['actionable', 'minimal'],
        help=("The callback plugin to use for generating output. "
              "See ansible-doc -t callback -l and ansible-doc -t callback [ansible|minimal]")
    )


def arg_limit(parser):
    parser.add_argument('-l', '--limit', metavar="SUBSET", help=(
        "further limit selected hosts to an additional pattern"
    ))
