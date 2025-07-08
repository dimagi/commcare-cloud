from memoized import memoized

from commcare_cloud.colors import color_error, color_summary, color_highlight, color_link
from .command_base import CommandBase, Argument


class Fab(CommandBase):
    command = 'fab'
    help = (
        "Placeholder for obsolete fab commands"
    )

    arguments = (
        Argument(dest='fab_command', help="""
        The name of the obsolete fab command.
        """, default=None, nargs="?"),
        Argument('-l', dest="list", action='store_true', help="""
        Use `-l` instead of a command to see the full list of commands.
        """),
    )

    def modify_parser(self):

        class _Parser(self.parser.__class__):
            @property
            @memoized
            def epilog(self_):
                return '\n'.join(_format_commands()).replace("<env>", "ENV")

        self.parser.__class__ = _Parser

    def run(self, args, unknown_args):
        if args.list or not args.fab_command:
            lines = _format_commands()
        else:
            if args.fab_command in ('deploy', 'awesome_deploy'):
                self.print_deploy_deprecation()
                return -1

            try:
                new_command = COMMANDS[args.fab_command]
            except KeyError:
                print(f"unknown command: {args.fab_command}")
                return -1

            lines = [color_error("This command is obsolete.") + " It has been replaced by", ""]
            lines.append(_format_command(new_command).lstrip('\n'))

        print("\n".join(lines))
        return -1

    @staticmethod
    def print_deploy_deprecation():
        print(color_summary('Hi. Things have changed.'))
        print()
        print('The `commcare-cloud <env> fab deploy` command has moved.')
        print('Instead, please use')
        print()
        print(color_highlight('  commcare-cloud <env> deploy'))
        print()
        print("For info on how you can use the new command, please see")
        print(
            color_link(
                "https://commcare-cloud.readthedocs.io/en/latest/reference/1-commcare-cloud/commands.html#deploy-command"  # noqa: E501
            )
        )
        print("or run")
        print()
        print(color_highlight('  commcare-cloud <env> deploy -h'))
        print()
        print("For more information on this change, please see")
        print(color_link("https://commcare-cloud.readthedocs.io/en/latest/changelog/0029-add-deploy-command.html"))
        print()
        print(color_summary('Thank you for using commcare-cloud.'))
        print()


def _format_commands():
    lines = [
        str(color_error("Obsolete fab commands:")),
        "",
        "Obsolete fab command       Replaced by 'commcare-cloud <env> ...'",
        "--------------------       --------------------------------------"
    ]
    lines.extend(sorted(f"{k:<25}  {v}" for k, v in COMMANDS.items()))
    return lines


def _format_command(cmd):
    return (
        f"  commcare-cloud <env> {cmd}"
        .replace("                           ", "  commcare-cloud <env> ")
    )


COMMANDS = {
    "preindex_views": "preindex-views",
    "kill_stale_celery_workers": "kill-stale-celery-workers",
    "rollback_formplayer": "ansible-playbook rollback_formplayer.yml --tags=rollback",
    "setup_limited_release": "deploy commcare --private [--keep-days=N] [--commcare-rev=HQ_BRANCH]",
    "setup_release": "deploy commcare --private --limit=all [--keep-days=N] [--commcare-rev=HQ_BRANCH]",
    "update_current": "deploy commcare --resume=RELEASE_NAME",
    "rollback": """deploy commcare --resume=PREVIOUS_RELEASE

Use the 'list-releases' command to get valid release names.
    """,
    "clean_releases": "clean-releases [--keep=N]",
    "manage": "django-manage",
    "deploy_commcare": "deploy commcare",
    "supervisorctl": "service NAME ACTION",
    "restart_services": "service commcare restart",
    "stop_celery": "service celery stop",
    "start_celery": "service celery start",
    "restart_webworkers": "service webworker restart",
    "stop_pillows": "service pillowtop stop",
    "start_pillows": "service pillowtop start",
    "check_status": """ping all
                           service postgresql status
                           service elasticsearch status
    """,
    "perform_system_checks": "perform-system-checks",
}
