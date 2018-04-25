from abc import ABCMeta, abstractmethod, abstractproperty
from collections import defaultdict
from itertools import groupby

import six
from clint.textui import puts, colored

from commcare_cloud.commands.ansible.helpers import AnsibleContext, get_django_webworker_name, \
    get_formplayer_spring_instance_name, get_formplayer_instance_name
from commcare_cloud.commands.ansible.run_module import run_ansible_module
from commcare_cloud.commands.celery_utils import get_celery_workers
from commcare_cloud.commands.command_base import CommandBase
from commcare_cloud.environment.main import get_environment
from commcare_cloud.fab.exceptions import NoHostsMatch

ACTIONS = ['start', 'stop', 'restart', 'status']

STATES = {
    'start': 'started',
    'stop': 'stopped',
    'restart': 'restarted',
    'status': 'status'
}


class ServiceBase(six.with_metaclass(ABCMeta)):
    @abstractproperty
    def name(self):
        raise NotImplementedError

    @abstractproperty
    def inventory_groups(self):
        raise NotImplementedError

    def __init__(self, environment, ansible_context):
        self.environment = environment
        self.ansible_context = ansible_context

    def run(self, action, host_pattern=None, process_pattern=None):
        try:
            return self.execute_action(action, host_pattern, process_pattern)
        except NoHostsMatch:
            only = limit = ''
            if process_pattern:
                only = " '--only={}'".format(process_pattern)
            if host_pattern:
                limit = " '--limit={}'".format(host_pattern)

            puts(colored.red("No '{}' hosts match{}{}".format(self.name, limit, only)))
            return 1

    @abstractmethod
    def execute_action(self, action, host_pattern=None, process_pattern=None):
        raise NotImplementedError

    def _run_ansible_module(self, host_pattern, module, module_args):
        return run_ansible_module(
            self.environment,
            self.ansible_context,
            host_pattern,
            module,
            module_args,
            True,
            None,
        )


class SubServicesMixin(six.with_metaclass(ABCMeta)):
    @abstractmethod
    def get_managed_services(self):
        raise NotImplementedError


class SupervisorService(SubServicesMixin, ServiceBase):
    def execute_action(self, action, host_pattern=None, process_pattern=None):
        if host_pattern:
            self.environment.inventory_manager.subset(host_pattern)

        process_host_mapping = self._get_processes_by_host(process_pattern)

        exit_status = []
        for hosts, processes in process_host_mapping.items():
            command = 'supervisorctl {} {}'.format(
                action,
                ' '.join(processes)
            )
            exit_status.append(self._run_ansible_module(
                ','.join(hosts),
                'shell',
                command
            ))
        if not exit_status:
            raise NoHostsMatch
        return max(exit_status)

    @abstractmethod
    def _get_processes_by_host(self, process_pattern=None):
        """
        :param process_pattern: process pattern from the args or None
        :return: dict mapping tuple(hostname1,hostname2,...) -> [process name list]
        """
        raise NotImplemented

    @property
    def all_service_hosts(self):
        pattern = ','.join(self.inventory_groups)
        return set([
            host.name for host in self.environment.inventory_manager.get_hosts(pattern)
        ])


class AnsibleService(ServiceBase):
    """Service that is controlled via the ansible 'service' module"""

    @property
    def service_name(self):
        return self.name

    def execute_action(self, action, host_pattern=None, process_pattern=None):
        if action == 'status':
            host_pattern = host_pattern or ','.join(self.inventory_groups)
            command = 'service {} status'.format(self.service_name)
            return self._run_ansible_module(host_pattern, 'shell', command)

        host_pattern = host_pattern or ','.join(self.inventory_groups)
        service_args = 'name={} state={}'.format(self.service_name, STATES[action])
        return self._run_ansible_module(host_pattern, 'service', service_args)


class MultiAnsibleService(SubServicesMixin, AnsibleService):
    """Service that is made up of multiple other services e.g. RiakCS"""

    @abstractmethod
    def get_inventory_group_for_sub_process(self, sub_service):
        """
        :param sub_service: name of a sub-service
        :return: inventory group for that service
        """
        raise NotImplementedError

    def check_status(self, host_pattern=None, process_pattern=None):
        def _status(service_name, run_on):
            command = 'service {} status'.format(service_name)
            return self._run_ansible_module(run_on, 'shell', command)

        return self._run_action_on_hosts(_status, host_pattern, process_pattern)

    def execute_action(self, action, host_pattern=None, process_pattern=None):
        if action == 'status':
            return self.check_status(host_pattern, process_pattern)

        def _change_state(service_name, run_on, action=action):
            service_args = 'name={} state={}'.format(service_name, STATES[action])
            return self._run_ansible_module(run_on, 'service', service_args)

        return self._run_action_on_hosts(_change_state, host_pattern, process_pattern)

    def _run_action_on_hosts(self, action_fn, host_pattern, process_pattern):
        if host_pattern:
            self.environment.inventory_manager.subset(host_pattern)

        if process_pattern:
            assert process_pattern in self.get_managed_services(), (
                "{} does not match available sub-processes".format(process_pattern)
            )

            run_on = self.get_inventory_group_for_sub_process(process_pattern)
            hosts = self.environment.inventory_manager.get_hosts(run_on)
            if not hosts:
                raise NoHostsMatch
            run_on = ','.join([host.name for host in hosts])
            return action_fn(process_pattern, run_on)
        else:
            exit_codes = []
            for service in self.get_managed_services():
                run_on = self.get_inventory_group_for_sub_process(service)
                hosts = self.environment.inventory_manager.get_hosts(run_on)
                if hosts:
                    exit_codes.append(action_fn(service, run_on))
            return max(exit_codes)


class Postgresql(AnsibleService):
    name = 'postgresql'
    inventory_groups = ['postgresql', 'pg_standby']


class Pgbouncer(AnsibleService):
    name = 'pgbouncer'
    inventory_groups = ['postgresql']


class Nginx(AnsibleService):
    name = 'nginx'
    inventory_groups = ['proxy']


class Elasticsearch(AnsibleService):
    name = 'elasticsearch'
    inventory_groups = ['elasticsearch']


class Couchdb(AnsibleService):
    name = 'couchdb'
    inventory_groups = ['couchdb2']


class RabbitMq(AnsibleService):
    name = 'rabbitmq'
    inventory_groups = ['rabbitmq']
    service_name = 'rabbitmq-server'


class Redis(AnsibleService):
    name = 'redis'
    inventory_groups = ['redis']
    service_name = 'redis-server'


class Riakcs(MultiAnsibleService):
    name = 'riakcs'
    inventory_groups = ['riakcs', 'stanchion']

    def get_managed_services(self):
        return [
            'riak', 'riak-cs', 'stanchion'
        ]

    def get_inventory_group_for_sub_process(self, sub_process):
        return {
            'stanchion': 'stanchion'
        }.get(sub_process, 'riakcs')


class Kafka(MultiAnsibleService):
    name = 'kafka'
    inventory_groups = ['kafka', 'zookeeper']

    def get_managed_services(self):
        return [
            'kafka-server', 'zookeeper'
        ]

    def get_inventory_group_for_sub_process(self, sub_process):
        return {
            'stanchion': 'stanchion'
        }.get(sub_process, 'riakcs')


class SingleSupervisorService(SupervisorService):
    @abstractproperty
    def supervisor_process_name(self):
        raise NotImplementedError

    def _get_processes_by_host(self, process_pattern=None):
        return {
            tuple(self.all_service_hosts): self.supervisor_process_name()
        }


class Webworker(SingleSupervisorService):
    name = 'webworker'
    inventory_groups = ['webworkers']

    @property
    def supervisor_process_name(self):
        return get_django_webworker_name(self.environment)


class Formplayer(SupervisorService):
    name = 'formplayer'
    inventory_groups = ['formplayer']

    @property
    def supervisor_process_name(self):
        return get_formplayer_spring_instance_name(self.environment)


class Touchforms(SupervisorService):
    name = 'touchforms'
    inventory_groups = ['touchforms']

    @property
    def supervisor_process_name(self):
        return get_formplayer_instance_name(self.environment)


class Celery(SupervisorService):
    name = 'celery'
    inventory_groups = ['celery']

    def _get_processes_by_host(self, process_pattern=None):
        all_hosts = self.all_service_hosts

        worker_match = queue_match = None
        if process_pattern:
            if ':' in process_pattern:
                queue_match, worker_match = process_pattern.split(':')
                worker_match = int(worker_match)
            else:
                queue_match = process_pattern

        def matches(item, matcher):
            return matcher is None or matcher == item

        workers = get_celery_workers(self.environment)
        processes_by_host = defaultdict(set)
        for host, queue, worker_num, process_name in workers:
            if host in all_hosts \
                    and matches(queue, queue_match) \
                    and matches(worker_num, worker_match):
                processes_by_host[host].add(process_name)

        processes_by_hosts = {}
        # group hosts together so we do less calls to ansible
        for grouper in groupby(processes_by_host.items(), key=lambda hp: hp[1]):
            hosts = tuple(host_processes[0] for host_processes in grouper[1])
            processes = grouper[0]
            processes_by_hosts[hosts] = processes
        return processes_by_hosts

    def get_managed_services(self):
        workers = get_celery_workers(self.environment)
        return sorted({
            '{}{}'.format(queue, ':{}'.format(worker_num) if worker_num > 1 else '')
            for host, queue, worker_num, process_name in workers
        })


SERVICES = [
    Postgresql,
    Pgbouncer,
    Nginx,
    Couchdb,
    RabbitMq,
    Elasticsearch,
    Redis,
    Riakcs,
    Kafka,
    Webworker,
    Formplayer,
    Touchforms,
    Celery,
]

SERVICE_NAMES = sorted([
    service.name for service in SERVICES
])

SERVICES_BY_NAME = {
    service.name: service for service in SERVICES
}


class Service(CommandBase):
    command = 'service'

    def make_parser(self):
        self.parser.add_argument(
            'services',
            nargs="+",
            choices=SERVICE_NAMES,
            help="The services to run the command on"
        )
        self.parser.add_argument(
            'action', choices=ACTIONS,
            help="What action to take"
        )
        self.parser.add_argument('--limit', help=(
            "Restrict the hosts to run the command on. Use 'help' action to list all option."
        ))
        self.parser.add_argument('--only', help=(
            "Sub-service name to limit action to. Use 'help' action to list all option."
        )
                                 )

    def run(self, args, unknown_args):
        environment = get_environment(args.env_name)

        services = [
            SERVICES_BY_NAME[name]
            for name in args.services
        ]

        ansible_context = AnsibleContext(args)
        exit_codes = []
        for service_cls in services:
            service = service_cls(environment, ansible_context)
            exit_codes.append(service.run(args.action, args.limit))
        return max(exit_codes)
