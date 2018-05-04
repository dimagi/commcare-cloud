import os

from commcare_cloud.commands.command_base import Argument

INVENTORY_GROUP_ARG = Argument('inventory_group', help=(
    "The inventory group to run the command on. Use 'all' for all hosts."
))

SKIP_CHECK_ARG = Argument('--skip-check', action='store_true', default=False, help=(
    "skip the default of viewing --check output first"
))

QUIET_ARG = Argument('--quiet', action='store_true', default=False, help=(
    "skip all user prompts and proceed as if answered in the affirmative"
))

BRANCH_ARG = Argument('--branch', default='master', help=(
    "the name of the commcare-cloud git branch to run against, if not master"
))

STDOUT_CALLBACK_ARG = Argument(
    '--output', dest='stdout_callback', choices=['actionable', 'minimal'],
    default=os.environ.get('ANSIBLE_STDOUT_CALLBACK') or 'default',
    help=("The callback plugin to use for generating output. "
          "See `ansible-doc -t callback -l` and `ansible-doc -t callback [ansible|minimal]`"),
    include_in_docs=False,
)

LIMIT_ARG = Argument('-l', '--limit', metavar="SUBSET", help=(
    "further limit selected hosts to an additional pattern"
), include_in_docs=False)
