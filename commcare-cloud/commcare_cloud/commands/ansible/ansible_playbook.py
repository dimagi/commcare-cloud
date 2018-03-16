# coding=utf-8
import os
import subprocess
from collections import defaultdict

from six.moves import shlex_quote
from clint.textui import puts, colored
from commcare_cloud.cli_utils import ask, has_arg, check_branch, print_command
from commcare_cloud.commands.ansible.helpers import (
    AnsibleContext, DEPRECATED_ANSIBLE_ARGS,
    get_common_ssh_args,
    get_celery_worker_name,
    get_django_webworker_name,
    get_formplayer_instance_name,
    get_formplayer_spring_instance_name,
)
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
    5. Check status or act on celery workers
        commcare-cloud staging service celery status
        commcare-cloud staging service celery restart
        commcare-cloud staging service celery restart --only=saved_exports_queue,pillow_retry_queue
    6. Check status or act on web workers
        commcare-cloud staging service webworkers status
        commcare-cloud staging service webworkers restart
    7. Check status or act on formplayer and formplayer-spring
        commcare-cloud staging service formplayer status
        commcare-cloud staging service formplayer restart --only=formplayer-spring
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
        'celery': ['celery'],
        'webworkers': ['webworkers'],
        'formplayer': ['formplayer', 'formplayer-spring']
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
                "For Celery, this can be Celery worker names as appearing in app-processes.yml. "
                "This can also be a comma-separated list of workers"
                "For ex: Run 'commcare-cloud staging celery status --only=sms_queue,email_queue'"
            )
        )

    def get_inventory_group_for_service(self, service, service_group):
        return self.INVENTORY_GROUP_FOR_SERVICE.get(service, service_group)

    @staticmethod
    def _get_celery_processes(env):
        environment = get_environment(env)
        app_processes_config = environment.translated_app_processes_config
        return app_processes_config.celery_processes

    def get_celery_config(self, args):
        """
        :return:
        celery_worker_config: a worker name mapped to list for full worker names per host
        {'submission_reprocessing_queue':
          {'hqcelery0.internal-va.commcarehq.org':
            ['commcare-hq-production-celery_submission_reprocessing_queue_0']
          }
        },
        """
        celery_worker_config = {}
        celery_processes = self._get_celery_processes(args.environment)
        for host, celery_processes_list in celery_processes.items():
            if host != 'None':
                for worker_name, details in celery_processes_list.items():
                    # split comma separated names to individual workers
                    for worker in worker_name.split(','):
                        # ignore flower and celery periodic as celery workers
                        if worker not in ['flower', 'celery_periodic']:
                            if not celery_worker_config.get(worker):
                                celery_worker_config[worker] = defaultdict(list)

                            if details.get('num_workers', 1) > 2:
                                for num in range(details.get('num_workers')):
                                    full_worker_name = get_celery_worker_name(args.environment, worker_name, num)
                                    celery_worker_config[worker][host].append(full_worker_name)
                            else:
                                full_worker_name = get_celery_worker_name(args.environment, worker_name, 0)
                                celery_worker_config[worker][host].append(full_worker_name)
        return celery_worker_config

    def get_workers_to_work_on(self, args):
        """
        :return:
        workers_by_host: full name of workers per host to work on
        """
        celery_config = self.get_celery_config(args)
        # full name of workers per host to run an action on
        workers_by_host = defaultdict(set)
        if args.only:
            for worker_name in args.only.split(','):
                for host, full_worker_names in celery_config[worker_name].items():
                    workers_by_host[host].update(full_worker_names)
        else:
            for worker_name in celery_config:
                for host, full_worker_names in celery_config[worker_name].items():
                    workers_by_host[host].update(full_worker_names)
        return workers_by_host

    def run_for_celery(self, service_group, action, args, unknown_args):
        exit_code = 0
        service = "celery"
        if action == "status" and not args.only:
            args.shell_command = "supervisorctl %s" % action
            args.inventory_group = self.get_inventory_group_for_service(service, args.service_group)
            exit_code = RunShellCommand(self.parser).run(args, unknown_args)
        else:
            workers_by_host = self.get_workers_to_work_on(args)
            puts(colored.blue("This is going to run the following"))
            for host, workers in workers_by_host.items():
                puts(colored.green('Host: [' + host + ']'))
                puts(colored.green("supervisorctl %s %s" % (action, ' '.join(workers))))

            if not ask('Good to go?', strict=True, quiet=args.quiet):
                return 0  # exit code

            for host, workers in workers_by_host.items():
                args.inventory_group = self.get_inventory_group_for_service(service, args.service_group)
                # if not applicable for all hosts then limit to a host
                if host != "*":
                    unknown_args.append('--limit=%s' % host)
                args.shell_command = "supervisorctl %s %s" % (action, ' '.join(workers))
                for service in self.services(service_group, args):
                    exit_code = RunShellCommand(self.parser).run(args, unknown_args)
                    if exit_code is not 0:
                        return exit_code
        return exit_code

    def run_for_webworkers(self, service_group, action, args, unknown_args):
        exit_code = 0
        django_webworker_name = get_django_webworker_name(args.environment)
        for service in self.services(service_group, args):
            args.inventory_group = self.get_inventory_group_for_service(service, args.service_group)
            args.shell_command = "supervisorctl %s %s" % (action, django_webworker_name)
            exit_code = RunShellCommand(self.parser).run(args, unknown_args)
            if exit_code is not 0:
                return exit_code
        return exit_code

    def run_for_formplayer(self, service_group, action, args, unknown_args):
        exit_code = 0
        ansible_context = AnsibleContext(args)
        for service in self.services(service_group, args):
            args.inventory_group = self.get_inventory_group_for_service(service, args.service_group)
            if service == "formplayer":
                formplayer_instance_name = get_formplayer_instance_name(args.environment)
                args.shell_command = "supervisorctl %s %s" % (action, formplayer_instance_name)
            elif service == "formplayer-spring":
                formplayer_spring_instance_name = get_formplayer_spring_instance_name(args.environment)
                args.shell_command = "supervisorctl %s %s" % (action, formplayer_spring_instance_name)
            exit_code = RunShellCommand(self.parser).run(args, unknown_args, ansible_context)
            if exit_code is not 0:
                return exit_code
        return exit_code

    def run_status_for_service_group(self, service_group, args, unknown_args):
        exit_code = 0
        ansible_context = AnsibleContext(args)
        args.silence_warnings = True
        if service_group == "formplayer":
            exit_code = self.run_for_formplayer(service_group, 'status', args, unknown_args)
        else:
            for service in self.services(service_group, args):
                if service == "celery":
                    exit_code = self.run_for_celery(service_group, 'status', args, unknown_args)
                elif service == "webworkers":
                    exit_code = self.run_for_webworkers(service_group, 'status', args, unknown_args)
                else:
                    if service == "redis":
                        args.shell_command = "redis-cli ping"
                    else:
                        args.shell_command = "service %s status" % self.SERVICE_PACKAGES_FOR_SERVICE.get(service, service)
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

    def run_supervisor_for_service_group(self, service_group, args, unknown_args):
        exit_code = 0
        if service_group == "celery":
            exit_code = self.run_for_celery(service_group, args.action, args, unknown_args)
        elif service_group == "webworkers":
            exit_code = self.run_for_webworkers(service_group, args.action, args, unknown_args)
        elif service_group == "formplayer":
            exit_code = self.run_for_formplayer(service_group, args.action, args, unknown_args)
        return exit_code

    def services(self, service_group, args):
        if service_group != 'celery' and args.only:
            return args.only.split(',')
        else:
            return self.SERVICES[service_group]

    def run_for_es(self, args, unknown_args):
        action = args.action
        if action == "restart":
            return RestartElasticsearch(self.parser).run(args, unknown_args)
        else:
            return self.run_ansible_module_for_service_group("es", args, unknown_args)

    def ensure_permitted_celery_only_options(self, args):
        celery_config = self.get_celery_config(args)
        # full name of workers per host to run an action on
        if args.only:
            for worker_name in args.only.split(','):
                assert worker_name in celery_config, \
                        "%s not found in the list of possible worker names, %s" % (
                            worker_name, celery_config.keys()
                        )

    def ensure_permitted_only_options(self, service_group, args):
        services = self.services(service_group, args)
        for service in services:
            if service == "celery":
                self.ensure_permitted_celery_only_options(args)
            else:
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
            exit_code = self.run_ansible_module_for_service_group('pg_standby', args, unknown_args,
                                                                  inventory_group="pg_standby")
        elif service_group in ["celery", "webworkers", "formplayer"]:
            exit_code = self.run_supervisor_for_service_group(service_group, args, unknown_args)
        return exit_code

    def run(self, args, unknown_args):
        service_group = args.service_group
        args.remote_user = 'ansible'
        args.become = True
        args.become_user = False
        args.silence_warnings = True
        if args.only:
            self.ensure_permitted_only_options(service_group, args)
        action = args.action
        if action == "status":
            exit_code = self.run_status_for_service_group(service_group, args, unknown_args)
        else:
            exit_code = self.perform_action(service_group, args, unknown_args)
        return exit_code
