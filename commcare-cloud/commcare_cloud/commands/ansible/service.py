from collections import defaultdict

from clint.textui import puts, colored

from commcare_cloud.cli_utils import ask
from commcare_cloud.commands.ansible.ansible_playbook import _AnsiblePlaybookAlias, \
    AnsiblePlaybook, RestartElasticsearch
from commcare_cloud.commands.ansible.helpers import get_django_webworker_name, \
    get_formplayer_instance_name, get_formplayer_spring_instance_name
from commcare_cloud.commands.ansible.run_module import RunShellCommand, RunAnsibleModule
from commcare_cloud.commands.celery_utils import get_celery_workers_config, \
    find_celery_worker_name


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
        commcare-cloud staging service celery restart --only=saved_exports_queue:1,pillow_retry_queue:2
    6. Check status or act on web workers
        commcare-cloud staging service webworkers status
        commcare-cloud staging service webworkers restart
    7. Check status or act on formplayer
        commcare-cloud staging service formplayer status
        commcare-cloud staging service formplayer restart
    8. Check status or act on touchforms
        commcare-cloud staging service touchforms status
        commcare-cloud staging service touchforms restart
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
        'formplayer': ['formplayer-spring'],
        'touchforms': ['formplayer'],
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
    def get_celery_workers_to_work_on(args):
        """
        :return:
        workers_by_host: full name of workers per host to work on
        """
        celery_config = get_celery_workers_config(args.environment)
        # full name of workers per host to run an action on
        workers_by_host = defaultdict(set)
        if args.only:
            for queue_name in args.only.split(','):
                worker_num = None
                if ':' in queue_name:
                    queue_name, worker_num = queue_name.split(':')
                for host, celery_worker_names in celery_config[queue_name].items():
                    if worker_num:
                        celery_worker_name = find_celery_worker_name(
                            args.environment, queue_name, host, worker_num)
                        assert celery_worker_name, \
                            "Could not find the celery worker for queue {queue_name} with index {worker_num}".format(
                                queue_name=queue_name, worker_num=worker_num
                            )
                        workers_by_host[host].add(celery_worker_name)
                    else:
                        workers_by_host[host].update(celery_worker_names)
                    workers_by_host[host].update(celery_worker_names)
        else:
            for queue_name in celery_config:
                for host, celery_worker_names in celery_config[queue_name].items():
                    workers_by_host[host].update(celery_worker_names)
        return workers_by_host

    def run_for_celery(self, service_group, action, args, unknown_args):
        exit_code = 0
        service = "celery"
        if action == "status" and not args.only:
            args.shell_command = "supervisorctl %s" % action
            args.inventory_group = self.get_inventory_group_for_service(service, args.service_group)
            exit_code = RunShellCommand(self.parser).run(args, unknown_args)
        else:
            workers_by_host = self.get_celery_workers_to_work_on(args)
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

    @staticmethod
    def get_supervisor_program_name(service, environment_name):
        if service == "webworkers":
            return get_django_webworker_name(environment_name)
        elif service == "formplayer":
            return get_formplayer_instance_name(environment_name)
        elif service == "formplayer-spring":
            return get_formplayer_spring_instance_name(environment_name)

    def run_supervisor_action_for_service_group(self, service_group, action, args, unknown_args):
        exit_code = 0
        for service in self.services(service_group, args):
            args.inventory_group = self.get_inventory_group_for_service(service, args.service_group)
            supervisor_command_name = self.get_supervisor_program_name(service, args.environment)
            args.shell_command = "supervisorctl %s %s" % (action, supervisor_command_name)
            exit_code = RunShellCommand(self.parser).run(args, unknown_args)
            if exit_code is not 0:
                return exit_code
        return exit_code

    def run_status_for_service_group(self, service_group, args, unknown_args):
        exit_code = 0
        args.silence_warnings = True
        if service_group in ["touchforms", "formplayer", "webworkers"]:
            exit_code = self.run_supervisor_action_for_service_group(service_group, 'status', args, unknown_args)
        else:
            for service in self.services(service_group, args):
                if service == "celery":
                    exit_code = self.run_for_celery(service_group, 'status', args, unknown_args)
                else:
                    if service == "redis":
                        args.shell_command = "redis-cli ping"
                    else:
                        args.shell_command = "service %s status" % self.SERVICE_PACKAGES_FOR_SERVICE.get(service, service)
                    args.inventory_group = self.get_inventory_group_for_service(service, args.service_group)
                    exit_code = RunShellCommand(self.parser).run(args, unknown_args)
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
        elif service_group in ["webworkers", "formplayer", "touchforms"]:
            exit_code = self.run_supervisor_action_for_service_group(service_group, args.action, args, unknown_args)
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

    @staticmethod
    def ensure_permitted_celery_only_options(args):
        celery_config = get_celery_workers_config(args.environment)
        # full name of workers per host to run an action on
        if args.only:
            for queue_name in args.only.split(','):
                if ':' in queue_name:
                    queue_name, woker_num = queue_name.split(':')
                assert queue_name in celery_config, \
                    "%s not found in the list of possible queues, %s" % (
                        queue_name, celery_config.keys()
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
        elif service_group in ["celery", "webworkers", "formplayer", "touchforms"]:
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
