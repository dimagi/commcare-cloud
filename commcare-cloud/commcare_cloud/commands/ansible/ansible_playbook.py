# coding=utf-8
import os
import subprocess
from six.moves import shlex_quote
from clint.textui import puts, colored
from commcare_cloud.cli_utils import ask, has_arg, check_branch, print_command
from commcare_cloud.commands.ansible.helpers import (
    AnsibleContext, DEPRECATED_ANSIBLE_ARGS,
    get_common_ssh_args,
    AnsibleOptions,
)
from commcare_cloud.commands.command_base import CommandBase
from commcare_cloud.commands.shared_args import arg_inventory_group, arg_skip_check, arg_quiet, \
    arg_branch, arg_stdout_callback
from commcare_cloud.environment.main import get_environment
from commcare_cloud.parse_help import add_to_help_text, filtered_help_message
from commcare_cloud.environment.paths import ANSIBLE_DIR
from commcare_cloud.commands.ansible.run_module import (
    RunAnsibleModule,
)


class AnsiblePlaybook(CommandBase):
    command = 'ansible-playbook'
    help = (
        "Run a playbook as you would with ansible-playbook, "
        "but with boilerplate settings already set based on your <environment>. "
        "By default, you will see --check output and then asked whether to apply. "
    )
    aliases = ('ap',)

    def make_parser(self):
        arg_skip_check(self.parser)
        arg_quiet(self.parser)
        arg_branch(self.parser)
        arg_stdout_callback(self.parser)
        self.parser.add_argument('playbook', help=(
            "The ansible playbook .yml file to run."
        ))
        add_to_help_text(self.parser, "\n{}\n{}".format(
            "The ansible-playbook options below are available as well",
            filtered_help_message(
                "ansible-playbook -h",
                below_line='Options:',
                above_line=None,
                exclude_args=DEPRECATED_ANSIBLE_ARGS + [
                    '--help',
                    '--diff',
                    '--check',
                    '-i',
                    '--ask-vault-pass',
                    '--vault-password-file',
                ],
            )
        ))

    def run(self, args, unknown_args):
        environment = get_environment(args.environment)
        ansible_context = AnsibleContext(args)
        check_branch(args)
        public_vars = environment.public_vars
        ask_vault_pass = public_vars.get('commcare_cloud_use_vault', True)

        def ansible_playbook(environment, playbook, *cmd_args):
            cmd_parts = (
                'ansible-playbook',
                os.path.join(ANSIBLE_DIR, '{playbook}'.format(playbook=playbook)),
                '-i', environment.paths.inventory_ini,
                '-e', '@{}'.format(environment.paths.vault_yml),
                '-e', '@{}'.format(environment.paths.public_yml),
                '--diff',
            ) + cmd_args

            if not has_arg(unknown_args, '-u', '--user'):
                cmd_parts += ('-u', 'ansible')

            if not has_arg(unknown_args, '-f', '--forks'):
                cmd_parts += ('--forks', '15')

            known_hosts_filepath = environment.paths.known_hosts
            if os.path.exists(known_hosts_filepath):
                cmd_parts += ("--ssh-common-args='-o=UserKnownHostsFile=%s'" % (known_hosts_filepath,), )

            if has_arg(unknown_args, '-D', '--diff') or has_arg(unknown_args, '-C', '--check'):
                puts(colored.red("Options --diff and --check not allowed. Please remove -D, --diff, -C, --check."))
                puts("These ansible-playbook options are managed automatically by commcare-cloud and cannot be set manually.")
                exit(2)

            if ask_vault_pass:
                cmd_parts += ('--vault-password-file=/bin/cat',)

            cmd_parts += get_common_ssh_args(public_vars)
            cmd = ' '.join(shlex_quote(arg) for arg in cmd_parts)
            print_command(cmd)
            p = subprocess.Popen(cmd, stdin=subprocess.PIPE, shell=True, env=ansible_context.env_vars)
            if ask_vault_pass:
                p.communicate(input='{}\n'.format(ansible_context.get_ansible_vault_password()))
            else:
                p.communicate()
            return p.returncode

        def run_check():
            return ansible_playbook(environment, args.playbook, '--check', *unknown_args)

        def run_apply():
            return ansible_playbook(environment, args.playbook, *unknown_args)

        exit_code = 0

        if args.skip_check:
            user_wants_to_apply = ask('Do you want to apply without running the check first?',
                                      quiet=args.quiet)
        else:
            exit_code = run_check()
            if exit_code == 1:
                # this means there was an error before ansible was able to start running
                exit(exit_code)
                return  # for IDE
            elif exit_code == 0:
                puts(colored.green(u"✓ Check completed with status code {}".format(exit_code)))
                user_wants_to_apply = ask('Do you want to apply these changes?',
                                          quiet=args.quiet)
            else:
                puts(colored.red(u"✗ Check failed with status code {}".format(exit_code)))
                user_wants_to_apply = ask('Do you want to try to apply these changes anyway?',
                                          quiet=args.quiet)

        if user_wants_to_apply:
            exit_code = run_apply()
            if exit_code == 0:
                puts(colored.green(u"✓ Apply completed with status code {}".format(exit_code)))
            else:
                puts(colored.red(u"✗ Apply failed with status code {}".format(exit_code)))

        exit(exit_code)


class _AnsiblePlaybookAlias(CommandBase):
    def make_parser(self):
        arg_skip_check(self.parser)
        arg_quiet(self.parser)
        arg_branch(self.parser)
        arg_stdout_callback(self.parser)


class DeployStack(_AnsiblePlaybookAlias):
    command = 'deploy-stack'
    aliases = ('aps',)
    help = (
        "Run the ansible playbook for deploying the entire stack. "
        "Often used in conjunction with --limit and/or --tag for a more specific update."
    )

    def run(self, args, unknown_args):
        args.playbook = 'deploy_stack.yml'
        AnsiblePlaybook(self.parser).run(args, unknown_args)


class UpdateConfig(_AnsiblePlaybookAlias):
    command = 'update-config'
    help = (
        "Run the ansible playbook for updating app config "
        "such as django localsettings.py and formplayer application.properties."
    )

    def run(self, args, unknown_args):
        args.playbook = 'deploy_localsettings.yml'
        unknown_args += ('--tags=localsettings',)
        AnsiblePlaybook(self.parser).run(args, unknown_args)


class AfterReboot(_AnsiblePlaybookAlias):
    command = 'after-reboot'
    help = (
        "Bring a just-rebooted machine back into operation. "
        "Includes mounting the encrypted drive."
    )

    def make_parser(self):
        super(AfterReboot, self).make_parser()
        arg_inventory_group(self.parser)

    def run(self, args, unknown_args):
        args.playbook = 'deploy_stack.yml'
        args.skip_check = True
        unknown_args += ('--tags=after-reboot', '--limit', args.inventory_group)
        AnsiblePlaybook(self.parser).run(args, unknown_args)


class RestartElasticsearch(_AnsiblePlaybookAlias):
    command = 'restart-elasticsearch'
    help = (
        "Do a rolling restart of elasticsearch."
    )

    def run(self, args, unknown_args):
        args.playbook = 'es_rolling_restart.yml'
        if not ask('Have you stopped all the elastic pillows?', strict=True, quiet=args.quiet):
            exit(0)
        puts(colored.yellow(
            "This will cause downtime on the order of seconds to minutes,\n"
            "except in a few cases where an index is replicated across multiple nodes."))
        if not ask('Do a rolling restart of the ES cluster?', strict=True, quiet=args.quiet):
            exit(0)
        AnsiblePlaybook(self.parser).run(args, unknown_args)


class BootstrapUsers(_AnsiblePlaybookAlias):
    command = 'bootstrap-users'
    help = (
        "Add users to a set of new machines as root. "
        "This must be done before any other user can log in."
    )

    def run(self, args, unknown_args):
        environment = get_environment(args.environment)
        args.playbook = 'deploy_stack.yml'
        args.skip_check = True
        public_vars = environment.public_vars
        root_user = public_vars.get('commcare_cloud_root_user', 'root')
        unknown_args += ('--tags=users', '-u', root_user)
        if not public_vars.get('commcare_cloud_pem'):
            unknown_args += ('--ask-pass',)
        AnsiblePlaybook(self.parser).run(args, unknown_args)


class UpdateUsers(_AnsiblePlaybookAlias):
    command = 'update-users'
    help = (
        "Add users to a set of new machines as root. "
        "This must be done before any other user can log in."
    )

    def run(self, args, unknown_args):
        args.playbook = 'deploy_stack.yml'
        unknown_args += ('--tags=users',)
        AnsiblePlaybook(self.parser).run(args, unknown_args)


class ManageServices(AnsibleOptions, _AnsiblePlaybookAlias):
    """
    example usages
    1. To restart riak and stanchion only for riakcs
       only option can be skipped to restart all services which are a part of riakcs
       i.e riak, riak-cs and stanchion in that order
        commcare-cloud staging service riakcs restart --only riak stanchion riak-cs
    2. To start services under proxy i.e nginx
       You can still pass ansible options which are
       --user, --become, --become_user
        commcare-cloud staging service proxy start -b
    """
    command = 'service'
    help = (
        "Manage services."
    )
    SERVICES = {
        'proxy': 'nginx',
        'riakcs': ['riak', 'riak-cs', 'stanchion']
    }
    ACTIONS = ['start', 'stop', 'restart']

    def make_parser(self):
        super(ManageServices, self).make_parser()
        self.parser.add_argument(
            'inventory_group',
            choices=self.SERVICES,
            help="The inventory group to run the command on"
            )
        self.add_ansible_options()
        self.parser.add_argument(
            'action',
            choices=self.ACTIONS,
            help="What action to take"
        )
        self.parser.add_argument(
            '--only',
            nargs='+',
            help=(
                "Specific services to act on for the inventory group. "
                "Can mention multiple separated with empty spaces. "
                "Example Usage: --only riak stanchion"
            )
        )

    def for_proxy(self, args, unknown_args):
        action = args.action
        if action == 'start':
            state = 'started'
        elif action == 'restart':
            state = 'restarted'
        elif action == 'stop':
            state = 'stopped'
        args.module = 'service'
        args.module_args = "name=nginx state=%s" % state
        RunAnsibleModule(self.parser).run(
            args,
            unknown_args
        )

    def for_riakcs(self, args, unknown_args):
        tags = []
        action = args.action
        args.playbook = "restart_riakcs.yml"
        if args.only:
            # for options to act on certain services create tags
            services = args.only
            for service in services:
                tags.append("%s_%s" % (action, service))
        if tags:
            unknown_args += ('--tags=%s' % ','.join(tags),)
        AnsiblePlaybook(self.parser).run(args, unknown_args)

    def run(self, args, unknown_args):
        inventory_group = args.inventory_group
        if inventory_group == "proxy":
            self.for_proxy(args, unknown_args)
        elif inventory_group == "riakcs":
            self.for_riakcs(args, unknown_args)
