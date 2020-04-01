from __future__ import absolute_import
import os

from commcare_cloud.commands.command_base import Argument

INVENTORY_GROUP_ARG = Argument('inventory_group', help="""
Machines to run on. Is anything that could be used in as a value for
`hosts` in an playbook "play", e.g.
`all` for all machines,
`webworkers` for a single group,
`celery:pillowtop` for multiple groups, etc.
See the description in [this blog](http://goinbigdata.com/understanding-ansible-patterns/)
for more detail in what can go here.
""")

SKIP_CHECK_ARG = Argument('--skip-check', action='store_true', default=False, help=(
    "skip the default of viewing --check output first"
), include_in_docs=False)

FACTORY_AUTH_ARG = Argument('--use-factory-auth', action='store_true', default=False, help=(
    "authenticate using the pem file (or prompt for root password if there is no pem file)"
))

QUIET_ARG = Argument('--quiet', action='store_true', default=False, help=(
    "skip all user prompts and proceed as if answered in the affirmative"
), include_in_docs=False)

BRANCH_ARG = Argument('--branch', default='master', help=(
    "the name of the commcare-cloud git branch to run against, if not master"
), include_in_docs=False)

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
