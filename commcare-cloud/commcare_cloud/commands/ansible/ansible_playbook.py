# coding=utf-8
import os
import subprocess
from six.moves import shlex_quote
from clint.textui import puts, colored
from commcare_cloud.cli_utils import ask, has_arg, check_branch, print_command
from commcare_cloud.commands.ansible.helpers import (
    AnsibleContext, DEPRECATED_ANSIBLE_ARGS,
    get_common_ssh_args,
    get_user_arg)
from commcare_cloud.commands.command_base import CommandBase
from commcare_cloud.commands.shared_args import arg_inventory_group, arg_skip_check, arg_quiet, \
    arg_branch, arg_stdout_callback
from commcare_cloud.environment.main import get_environment
from commcare_cloud.parse_help import add_to_help_text, filtered_help_message
from commcare_cloud.environment.paths import ANSIBLE_DIR
from commcare_cloud.commands.ansible.run_module import (
    RunAnsibleModule,
    RunShellCommand,
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

    def run(self, args, unknown_args, ansible_context=None):
        environment = get_environment(args.environment)
        environment.create_generated_yml()
        ansible_context = ansible_context or AnsibleContext(args)
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
                '-e', '@{}'.format(environment.paths.generated_yml),
                '--diff',
            ) + cmd_args

            cmd_parts += get_user_arg(public_vars, unknown_args)

            if not has_arg(unknown_args, '-f', '--forks'):
                cmd_parts += ('--forks', '15')

            known_hosts_filepath = environment.paths.known_hosts
            if os.path.exists(known_hosts_filepath):
                cmd_parts += ("--ssh-common-args='-o=UserKnownHostsFile=%s'" % (known_hosts_filepath,), )

            if has_arg(unknown_args, '-D', '--diff') or has_arg(unknown_args, '-C', '--check'):
                puts(colored.red("Options --diff and --check not allowed. Please remove -D, --diff, -C, --check."))
                puts("These ansible-playbook options are managed automatically by commcare-cloud and cannot be set manually.")
                return 2  # exit code

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
                return exit_code
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

        return exit_code


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
        return AnsiblePlaybook(self.parser).run(args, unknown_args)


class UpdateConfig(_AnsiblePlaybookAlias):
    command = 'update-config'
    help = (
        "Run the ansible playbook for updating app config "
        "such as django localsettings.py and formplayer application.properties."
    )

    def run(self, args, unknown_args):
        args.playbook = 'deploy_localsettings.yml'
        unknown_args += ('--tags=localsettings',)
        return AnsiblePlaybook(self.parser).run(args, unknown_args)


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
        return AnsiblePlaybook(self.parser).run(args, unknown_args)


class RestartElasticsearch(_AnsiblePlaybookAlias):
    command = 'restart-elasticsearch'
    help = (
        "Do a rolling restart of elasticsearch."
    )

    def run(self, args, unknown_args):
        args.playbook = 'es_rolling_restart.yml'
        if not ask('Have you stopped all the elastic pillows?', strict=True, quiet=args.quiet):
            return 0  # exit code
        puts(colored.yellow(
            "This will cause downtime on the order of seconds to minutes,\n"
            "except in a few cases where an index is replicated across multiple nodes."))
        if not ask('Do a rolling restart of the ES cluster?', strict=True, quiet=args.quiet):
            return 0  # exit code
        return AnsiblePlaybook(self.parser).run(args, unknown_args)


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
        return AnsiblePlaybook(self.parser).run(args, unknown_args)


class UpdateUsers(_AnsiblePlaybookAlias):
    command = 'update-users'
    help = (
        "Add users to a set of new machines as root. "
        "This must be done before any other user can log in."
    )

    def run(self, args, unknown_args):
        args.playbook = 'deploy_stack.yml'
        unknown_args += ('--tags=users',)
        return AnsiblePlaybook(self.parser).run(args, unknown_args)


class Service(_AnsiblePlaybookAlias):
    """
    example usages
    1. To restart riak and stanchion only for riakcs
       only option can be skipped to restart all services which are a part of riakcs
       This would always act on riak, riak-cs and stanchion, in that order
        commcare-cloud staging service riakcs restart --only=riak,stanchion
    2. To start services under proxy i.e nginx
        commcare-cloud staging service proxy restart
    3. To get status
        commcare-cloud staging service riakcs status
        commcare-cloud staging service riakcs status --only=stanchion
    4. Limit to hosts
        commcare-cloud staging service riakcs status --only=riak,riak-cs --limit=hqriak00-staging.internal-va.commcarehq.org
    """
    command = 'service'
    help = (
        "Manage services."
    )
    SERVICES = {
        # service_group: services
        'proxy': ['nginx'],
        'riakcs': ['riak', 'riak-cs', 'stanchion'],
        'stanchion': ['stanchion'],
        'es': ['elasticsearch'],
        'redis': ['redis'],
        'couchdb2': ['couchdb2'],
        'postgresql': ['postgresql', 'pgbouncer'],
        'rabbitmq': ['rabbitmq'],
        'kafka': ['kafka', 'zookeeper'],
        'pg_standby': ['postgresql', 'pgbouncer'],
    }
    ACTIONS = ['start', 'stop', 'restart', 'status']
    DESIRED_STATE_FOR_ACTION = {
        'start': 'started',
        'stop': 'stopped',
        'restart': 'restarted',
    }
    # add this mapping where service group is not same as the inventory group itself
    INVENTORY_GROUP_FOR_SERVICE = {
        'stanchion': 'stanchion',
        'elasticsearch': 'elasticsearch',
        'zookeeper': 'zookeeper',
    }
    # add this if the service package is not same as the service itself
    SERVICE_PACKAGES_FOR_SERVICE = {
        'rabbitmq': 'rabbitmq-server',
        'kafka': 'kafka-server'
    }
    # add this if the module name is not same as the service itself
    ANSIBLE_MODULE_FOR_SERVICE = {
        "redis": "redis-server",

    }

    def make_parser(self):
        super(Service, self).make_parser()
        self.parser.add_argument(
            'service_group',
            choices=self.SERVICES.keys(),
            help="The service group to run the command on"
            )
        self.parser.add_argument(
            'action',
            choices=self.ACTIONS,
            help="What action to take"
        )
        self.parser.add_argument(
            '--only',
            help=(
                "Specific comma separated services to act on for the service group. "
                "Example Usage: --only=riak,stanchion"
            )
        )

    def get_inventory_group_for_service(self, service, service_group):
        return self.INVENTORY_GROUP_FOR_SERVICE.get(service, service_group)

    def run_status_for_service_group(self, service_group, args, unknown_args):
        exit_code = 0
        ansible_context = AnsibleContext(args)
        for service in self.services(service_group, args):
            if service == "redis":
                args.shell_command = "redis-cli ping"
            else:
                args.shell_command = "service %s status" % self.SERVICE_PACKAGES_FOR_SERVICE.get(service, service)
                args.silence_warnings = True
            args.inventory_group = self.get_inventory_group_for_service(service, args.service_group)
            exit_code = RunShellCommand(self.parser).run(args, unknown_args, ansible_context)
            if exit_code is not 0:
                # if any service status check didn't go smoothly exit right away
                return exit_code
        return exit_code

    def run_ansible_module_for_service_group(self, service_group, args, unknown_args, inventory_group=None):
        for service in self.SERVICES[service_group]:
            action = args.action
            state = self.DESIRED_STATE_FOR_ACTION[action]
            args.inventory_group = (
                inventory_group or
                self.get_inventory_group_for_service(service, service_group))
            args.module = 'service'
            args.module_args = "name=%s state=%s" % (
                self.ANSIBLE_MODULE_FOR_SERVICE.get(service, service),
                state)
            return RunAnsibleModule(self.parser).run(
                args,
                unknown_args
            )

    def run_ansible_playbook_for_service_group(self, service_group, args, unknown_args):
        tags = []
        action = args.action
        state = self.DESIRED_STATE_FOR_ACTION[action]
        args.playbook = "service_playbooks/%s.yml" % service_group
        services = self.services(service_group, args)
        if args.only:
            # for options to act on certain services create tags
            for service in services:
                if service:
                    tags.append("%s_%s" % (action, service))
            if tags:
                unknown_args.append('--tags=%s' % ','.join(tags), )
        unknown_args.extend(['--extra-vars', "desired_state=%s desired_action=%s" % (state, action)])
        return AnsiblePlaybook(self.parser).run(args, unknown_args)

    def services(self, service_group, args):
        if args.only:
            return args.only.split(',')
        else:
            return self.SERVICES[service_group]

    def run_for_es(self, args, unknown_args):
        action = args.action
        if action == "restart":
            return RestartElasticsearch(self.parser).run(args, unknown_args)
        else:
            return self.run_ansible_module_for_service_group("es", args, unknown_args)

    def ensure_permitted_only_options(self, service_group, args):
        services = self.services(service_group, args)
        for service in services:
            assert service in self.SERVICES[service_group], \
                ("%s not allowed. Please use from %s for --only option" %
                 (service, self.SERVICES[service_group])
                 )

    def perform_action(self, service_group, args, unknown_args):
        exit_code = 0
        if service_group in ['proxy', 'redis', 'couchdb2', 'postgresql', 'rabbitmq']:
            exit_code = self.run_ansible_module_for_service_group(service_group, args, unknown_args)
        elif service_group in ['riakcs', 'kafka']:
            exit_code = self.run_ansible_playbook_for_service_group(service_group, args, unknown_args)
        elif service_group == "stanchion":
            if not args.only:
                args.only = "stanchion"
            exit_code = self.run_ansible_playbook_for_service_group('riakcs', args, unknown_args)
        elif service_group == "es":
            exit_code = self.run_for_es(args, unknown_args)
        elif service_group == "pg_standby":
            exit_code = self.run_ansible_module_for_service_group('pg_standby', args, unknown_args, inventory_group="pg_standby")
        return exit_code

    def run(self, args, unknown_args):
        service_group = args.service_group
        args.remote_user = 'ansible'
        args.become = True
        args.become_user = False
        if args.only:
            self.ensure_permitted_only_options(service_group, args)
        action = args.action
        if action == "status":
            exit_code = self.run_status_for_service_group(service_group, args, unknown_args)
        else:
            exit_code = self.perform_action(service_group, args, unknown_args)
        return exit_code
