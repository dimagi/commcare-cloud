import json

from commcare_cloud.commands import shared_args
from commcare_cloud.commands.ansible.helpers import AnsibleContext, run_action_with_check_mode
from commcare_cloud.commands.ansible.run_module import run_ansible_module
from commcare_cloud.commands.command_base import Argument, CommandBase


class CleanReleases(CommandBase):
    command = 'clean-releases'
    help = """
        Cleans old and failed deploys from the ~/www/ENV/releases/ directory.
    """

    arguments = (
        Argument('-k', '--keep', type=int, default=3, metavar="N", help="""
            The number of releases to retain. Default: 3
        """),
        Argument('-x', '--exclude', default=[], nargs="*", help="""
            Extra release names to exclude from cleanup, in addition to
            the automatic exclusions such as the current release.
        """),
        shared_args.QUIET_ARG,
        shared_args.SKIP_CHECK_ARG,
        shared_args.BRANCH_ARG,
    )

    def run(self, args, unknown_args):
        context = AnsibleContext(args)
        environment = context.environment
        extra_args = (f"--playbook-dir={environment.paths.ansible_path}",) + tuple(unknown_args)
        module_args = ["path={{www_home}}/releases", f"keep={args.keep}"]
        if args.exclude:
            module_args.append("exclude={{%s}}" % json.dumps(args.exclude))
        shared_dir = environment.fab_settings_config.shared_dir_for_staticfiles
        if shared_dir:
            module_args.append(f"shared_dir_for_staticfiles={shared_dir}")

        def run_ansible(*check):
            return run_ansible_module(
                context,
                "webworkers,celery,pillowtop,proxy,django_manage",
                "clean_releases",
                " ".join(module_args),
                become=True,
                become_user="{{ cchq_user }}",
                extra_args=check + extra_args,
            )

        def run_check():
            with environment.secrets_backend.suppress_datadog_event():
                return run_ansible('--check')

        return run_action_with_check_mode(run_check, run_ansible, args.skip_check, args.quiet)
