from abc import ABCMeta, abstractmethod, abstractproperty

import six

from commcare_cloud.commands.ansible.helpers import AnsibleContext
from commcare_cloud.commands.ansible.run_module import run_ansible_module
from commcare_cloud.commands.command_base import CommandBase
from commcare_cloud.environment.main import get_environment

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



class MultiAnsibleService(AnsibleService):
    """Service that is made up of multiple other services e.g. RiakCS"""

    @abstractmethod
    def get_inventory_group_for_sub_process(self, sub_service):
        """
        :param sub_service: name of a sub-service
        :return: inventory group for that service
        """
        raise NotImplementedError

    @abstractmethod
    def get_managed_services(self):
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


SERVICES = [
    Postgresql,
    Pgbouncer,
    Nginx,
    Couchdb,
    RabbitMq,
    Elasticsearch,
    Redis
    Riakcs
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
        for service_cls in services:
            service = service_cls(environment, ansible_context)
            service.run(args.action, args.limit)
