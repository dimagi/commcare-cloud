# coding=utf-8
from __future__ import absolute_import
from __future__ import print_function
from __future__ import unicode_literals
import os
import re
import subprocess
from copy import deepcopy

from clint.textui import puts
from six.moves import shlex_quote

from commcare_cloud.alias import commcare_cloud
from commcare_cloud.cli_utils import ask, has_arg, check_branch, print_command
from commcare_cloud.colors import color_error
from commcare_cloud.commands import shared_args
from commcare_cloud.commands.ansible.helpers import (
    AnsibleContext, DEPRECATED_ANSIBLE_ARGS,
    get_common_ssh_args,
    get_user_arg, run_action_with_check_mode)
from commcare_cloud.commands.command_base import CommandBase, Argument
from commcare_cloud.environment.main import get_environment
from commcare_cloud.environment.paths import ANSIBLE_DIR
from commcare_cloud.parse_help import add_to_help_text, filtered_help_message, ANSIBLE_HELP_OPTIONS_PREFIX


class AnsiblePlaybook(CommandBase):
    command = 'ansible-playbook'
    help = """
    Run a playbook as you would with ansible-playbook

    By default, you will see --check output and then asked whether to apply.
    
    Example:

    ```
    commcare-cloud <env> ansible-playbook deploy_proxy.yml --limit=proxy
    ```
    """
    aliases = ('ap',)
    arguments = (
        shared_args.SKIP_CHECK_ARG,
        shared_args.QUIET_ARG,
        shared_args.BRANCH_ARG,
        shared_args.STDOUT_CALLBACK_ARG,
        shared_args.FACTORY_AUTH_ARG,
        shared_args.LIMIT_ARG,
        Argument('playbook', help="""
            The ansible playbook .yml file to run.
            Options are the `*.yml` files located under `commcare_cloud/ansible`
            which is under `src` for an egg install and under
            `<virtualenv>/lib/python3.6/site-packages` for a wheel install.
        """)
    )

    def modify_parser(self):
        add_to_help_text(self.parser, "\n{}\n{}".format(
            "The ansible-playbook options below are available as well:",
            filtered_help_message(
                "ansible-playbook -h",
                below_line=ANSIBLE_HELP_OPTIONS_PREFIX,
                above_line=None,
                exclude_args=DEPRECATED_ANSIBLE_ARGS + [
                    '--help',
                    '--diff',
                    '--check',
                    '-i',
                    '--ask-vault-pass',
                    '--vault-password-file',
                    '--limit',
                ],
            )
        ))

    def run(self, args, unknown_args, always_skip_check=False, respect_ansible_skip=True):
        environment = get_environment(args.env_name)
        environment.create_generated_yml()
        ansible_context = AnsibleContext(args)
        check_branch(args)
        return run_ansible_playbook(
            environment, args.playbook, ansible_context, args.skip_check, args.quiet,
            always_skip_check, args.limit, args.use_factory_auth, unknown_args,
            respect_ansible_skip=respect_ansible_skip,
        )


def run_ansible_playbook(
        environment, playbook, ansible_context,
        skip_check=False, quiet=False, always_skip_check=False, limit=None,
        use_factory_auth=False, unknown_args=None, respect_ansible_skip=True,
    ):

    unknown_args = unknown_args or []

    def get_limit():
        limit_parts = []
        if limit:
            limit_parts = re.split('[,:]', limit)
        if 'ansible_skip' in environment.sshable_hostnames_by_group and respect_ansible_skip:
            limit_parts.append('!ansible_skip')

        if limit_parts:
            return '--limit', ','.join(limit_parts)
        else:
            return ()

    def ansible_playbook(environment, playbook, *cmd_args):
        if os.path.isabs(playbook):
            playbook_path = playbook
        else:
            playbook_path = os.path.join(ANSIBLE_DIR, '{playbook}'.format(playbook=playbook))
        cmd_parts = (
            'ansible-playbook',
            playbook_path,
            '-i', environment.paths.inventory_source,
            '-e', '@{}'.format(environment.paths.public_yml),
            '-e', '@{}'.format(environment.paths.generated_yml),
            '--diff',
        ) + get_limit() + cmd_args

        public_vars = environment.public_vars
        env_vars = ansible_context.env_vars
        cmd_parts += get_user_arg(public_vars, unknown_args, use_factory_auth)

        if has_arg(unknown_args, '-D', '--diff') or has_arg(unknown_args, '-C', '--check'):
            puts(color_error("Options --diff and --check not allowed. "
                             "Please remove -D, --diff, -C, --check."))
            puts(color_error("These ansible-playbook options are managed automatically "
                             "by commcare-cloud and cannot be set manually."))
            return 2  # exit code

        cmd_parts += environment.secrets_backend.get_extra_ansible_args()

        cmd_parts_with_common_ssh_args = get_common_ssh_args(environment, use_factory_auth=use_factory_auth)
        cmd_parts += cmd_parts_with_common_ssh_args
        cmd = ' '.join(shlex_quote(arg) for arg in cmd_parts)
        print_command(cmd)
        env_vars.update(environment.secrets_backend.get_extra_ansible_env_vars())
        return subprocess.call(cmd_parts, env=env_vars)

    def run_check():
        with environment.secrets_backend.suppress_datadog_event():
            return ansible_playbook(environment, playbook, '--check', *unknown_args)

    def run_apply():
        return ansible_playbook(environment, playbook, *unknown_args)

    return run_action_with_check_mode(run_check, run_apply, skip_check, quiet, always_skip_check)


class _AnsiblePlaybookAlias(CommandBase):
    arguments = (
        shared_args.SKIP_CHECK_ARG,
        shared_args.QUIET_ARG,
        shared_args.BRANCH_ARG,
        shared_args.STDOUT_CALLBACK_ARG,
        shared_args.FACTORY_AUTH_ARG,
        shared_args.LIMIT_ARG,
    )


class DeployStack(_AnsiblePlaybookAlias):
    command = 'deploy-stack'
    aliases = ('aps',)
    help = """
        Run the ansible playbook for deploying the entire stack.

        Often used in conjunction with --limit and/or --tag
        for a more specific update.
    """

    arguments = _AnsiblePlaybookAlias.arguments + (
        Argument('--first-time', action='store_true', help="""
        Use this flag for running against a newly-created machine.

        It will first use factory auth to set up users,
        and then will do the rest of deploy-stack normally,
        but skipping check mode.

        Running with this flag is equivalent to

        ```
        commcare-cloud <env> bootstrap-users <...args>
        commcare-cloud <env> deploy-stack --skip-check --skip-tags=users <...args>
        ```

        If you run and it fails half way, when you're ready to retry, you're probably
        better off running
        ```
        commcare-cloud <env> deploy-stack --skip-check --skip-tags=users <...args>
        ```
        since if it made it through bootstrap-users
        you won't be able to run bootstrap-users again.
        """),
    )

    def run(self, args, unknown_args):
        always_skip_check = False
        if args.first_time:
            if not self._check_new_machine_setup(args.limit, args.env_name):
                print('Bad configuration for new machine setup. Aborting.')
                exit(1)
            rc = BootstrapUsers(self.parser).run(deepcopy(args), deepcopy(unknown_args))
            if rc != 0:
                return rc
            # the above just ran --tags=users
            # no need to run it a second time
            unknown_args += ('--skip-tags=users',)
            args.quiet = True
            always_skip_check = True
        args.playbook = 'deploy_stack.yml'
        return AnsiblePlaybook(self.parser).run(
            args, unknown_args, always_skip_check=always_skip_check)

    def _check_new_machine_setup(self, limit, env_name):
        """
        There are some configurations that we allow for backwards compatibility
        but don't want new machines using.
        This method checks new machine setup and returns False if it contains undesirable config.
        Config is undesirable under any of the following conditions:
            - a host has `datavol_fstype` set to any value other than `ext4`
        """
        ok = True
        limit = limit or 'all'
        environment = get_environment(env_name)
        group_names = re.split(r'[:,]', limit)
        hosts = set()
        for group_name in group_names:
            if group_name in environment.groups:
                hosts.update(environment.groups[group_name])
        for host in hosts:
            host_vars = environment.get_host_vars(host)
            if host_vars.get('datavol_fstype', 'ext4') != 'ext4':
                ok = False
                val = host_vars.get('datavol_fstype')
                if val == 'xfs':
                    print('datavol_fstype=xfs is for backwards compatibility '
                          'and not allowed for new machine setup')
                else:
                    print('datavol_fstype={} is not an allowed value'.format(val))
        return ok


class UpdateConfig(CommandBase):
    command = 'update-config'
    help = """
    Run the ansible playbook for updating app config.

    This includes django `localsettings.py` and formplayer `application.properties`.
    """

    arguments = (shared_args.BRANCH_ARG,)

    def run(self, args, unknown_args):
        unknown_args += ('-e', '{"_should_update_formplayer_in_place": true}')
        rc = commcare_cloud(args.env_name, 'ansible-playbook', 'deploy_localsettings.yml',
                              tags='localsettings', branch=args.branch, *unknown_args)
        if rc == 0 and ask("Would you like to run Django checks to validate the settings?"):
            environment = get_environment(args.env_name)
            server_args = []
            try:
                limit_arg = unknown_args.index('--limit')
            except ValueError:
                pass
            else:
                servers = environment.inventory_manager.get_hosts(unknown_args[limit_arg + 1])
                server_args.extend(['--server', servers[0]])
            commcare_cloud(args.env_name, 'django-manage', *(['check', '--deploy'] + server_args))
            commcare_cloud(args.env_name, 'django-manage', *(['check', '--deploy', '-t', 'database'] + server_args))
            commcare_cloud(args.env_name, 'django-manage', *(['check_services'] + server_args))
        else:
            return rc


class AfterReboot(_AnsiblePlaybookAlias):
    command = 'after-reboot'
    help = """
    Bring a just-rebooted machine back into operation.

    Includes mounting the encrypted drive.
    This command never runs in check mode.
    """
    arguments = _AnsiblePlaybookAlias.arguments + (
        shared_args.INVENTORY_GROUP_ARG,
    )

    def run(self, args, unknown_args):
        args.playbook = 'deploy_stack.yml'
        if args.limit:
            args.limit = '{}:&{}'.format(args.limit, args.inventory_group)
        else:
            args.limit = args.inventory_group
        del args.inventory_group
        unknown_args += ('--tags', 'after-reboot',)
        return AnsiblePlaybook(self.parser).run(args, unknown_args, always_skip_check=True)


class BootstrapUsers(_AnsiblePlaybookAlias):
    command = 'bootstrap-users'
    help = """
        Add users to a set of new machines as root.

        This must be done before any other user can log in.

        This will set up machines to reject root login and require
        password-less logins based on the usernames and public keys
        you have specified in your environment. This can only be run once
        per machine; if after running it you would like to run it again,
        you have to use `update-users` below instead.
        """

    def run(self, args, unknown_args):
        environment = get_environment(args.env_name)
        args.playbook = 'deploy_stack.yml'
        args.use_factory_auth = True
        public_vars = environment.public_vars
        unknown_args += ('--tags=bootstrap-users',) + get_user_arg(public_vars, unknown_args, use_factory_auth=True)

        if not public_vars.get('commcare_cloud_pem'):
            unknown_args += ('--ask-pass',)
        return AnsiblePlaybook(self.parser).run(args, unknown_args, always_skip_check=True)


class UpdateUsers(_AnsiblePlaybookAlias):
    command = 'update-users'
    help = """
    Bring users up to date with the current CommCare Cloud settings.

    In steady state this command (and not `bootstrap-users`) should be used
    to keep machine user accounts, permissions, and login information
    up to date.
    """

    def run(self, args, unknown_args):
        args.playbook = 'deploy_stack.yml'
        unknown_args += ('--tags=users',)
        return AnsiblePlaybook(self.parser).run(args, unknown_args)


class UpdateUserPublicKey(_AnsiblePlaybookAlias):
    command = 'update-user-key'
    help = "Update a single user's public key (because update-users takes forever)."
    arguments = _AnsiblePlaybookAlias.arguments + (
        Argument("username", help="username who owns the public key"),
    )

    def run(self, args, unknown_args):
        args.playbook = 'deploy_stack.yml'
        unknown_args += (
            '--tags=pubkey',
            '--extra-vars={{"dev_users": {{"present": [{}]}}}}'.format(args.username),
        )
        return AnsiblePlaybook(self.parser).run(args, unknown_args)


class UpdateSupervisorConfs(_AnsiblePlaybookAlias):
    command = 'update-supervisor-confs'
    help = """
    Updates the supervisor configuration files for services required by CommCare.

    These services are defined in app-processes.yml.
    """

    def run(self, args, unknown_args):
        args.playbook = 'deploy_stack.yml'
        unknown_args += ('--tags=services',)
        rc = AnsiblePlaybook(self.parser).run(args, unknown_args)
        if ask("Would you like to update supervisor to use the new configurations?"):
            carryover_args = []
            if args.limit:
                carryover_args.extend(['--limit', args.limit])
            commcare_cloud(
                args.env_name, 'run-shell-command', 'webworkers:celery:pillowtop:formplayer',
                'supervisorctl reread; supervisorctl update', '-b', *carryover_args
            )
        else:
            return rc
