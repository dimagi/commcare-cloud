import re
from abc import ABCMeta, abstractmethod, abstractproperty
from collections import defaultdict, OrderedDict
from itertools import groupby

import attr
import six
from clint.textui import puts, colored, indent

from commcare_cloud.commands.ansible.helpers import (
    AnsibleContext, get_django_webworker_name,
    get_formplayer_spring_instance_name,
    get_formplayer_instance_name,
    get_celery_workers,
    get_pillowtop_processes
)
from commcare_cloud.commands.ansible.run_module import run_ansible_module
from commcare_cloud.commands.command_base import CommandBase, Argument
from commcare_cloud.environment.main import get_environment
from commcare_cloud.fab.exceptions import NoHostsMatch

ACTIONS = ['start', 'stop', 'restart', 'status', 'help']

STATES = {
    'start': 'started',
    'stop': 'stopped',
    'restart': 'restarted',
    'status': 'status'
}


@attr.s
class ServiceOption(object):
    name = attr.ib()
    sub_options = attr.ib(default=None)


class ServiceBase(six.with_metaclass(ABCMeta)):
    """Base class for all services."""

    @abstractproperty
    def name(self):
        """Name of the service shown on the command line."""
        raise NotImplementedError

    @abstractproperty
    def inventory_groups(self):
        """Inventory groups that are applicable to this service."""
        raise NotImplementedError

    def __init__(self, environment, ansible_context):
        self.environment = environment
        self.ansible_context = ansible_context

    def run(self, action, host_pattern=None, process_pattern=None):
        if action == 'help':
            self.print_help()
            return 0

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

    def print_help(self):
        puts(colored.green("Additional help for service '{}'".format(self.name)))

        options = self.get_options()
        for name, options in options.items():
            puts("{}:".format(name))
            with indent():
                for option in options:
                    puts(option.name)
                    if option.sub_options:
                        with indent():
                            puts(', '.join(option.sub_options))

    def get_options(self):
        all_group_options = []
        for group in self.inventory_groups:
            sub_groups = [g.name for g in self.environment.inventory_manager.groups[group].child_groups]
            all_group_options.append(ServiceOption(group, sub_groups))

        options = OrderedDict()
        options["Inventory groups (use with '--limit')"] = all_group_options
        options["Hosts (use with '--limit')"] = [ServiceOption(host) for host in self.all_service_hosts]
        return options

    @property
    def all_service_hosts(self):
        """
        :return: set of hosts that are applicable to this service
        """
        pattern = ','.join(self.inventory_groups)
        return set([
            host.name for host in self.environment.inventory_manager.get_hosts(pattern)
        ])

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
    @abstractproperty
    def managed_services(self):
        """
        :return: List of sub-services managed by this class. e.g. Celery workers, Pillowtop processes
        """
        raise NotImplementedError

    def get_options(self):
        options = super(SubServicesMixin, self).get_options()
        managed_services = self.managed_services
        if managed_services:
            options["Sub-services (use with --only)"] = [ServiceOption(service) for service in managed_services]
        return options


class SupervisorService(SubServicesMixin, ServiceBase):
    def execute_action(self, action, host_pattern=None, process_pattern=None):
        if host_pattern:
            self.environment.inventory_manager.subset(host_pattern)

        process_host_mapping = self._get_processes_by_host(process_pattern)

        if not process_host_mapping:
            raise NoHostsMatch

        non_zero_exits = []
        for hosts, processes in process_host_mapping.items():
            command = 'supervisorctl {} {}'.format(
                action,
                ' '.join(processes)
            )
            exit_code = self._run_ansible_module(
                ','.join(hosts),
                'shell',
                command
            )
            if exit_code != 0:
                non_zero_exits.append(exit_code)
        return non_zero_exits[0] if non_zero_exits else 0

    @abstractmethod
    def _get_processes_by_host(self, process_pattern=None):
        """
        Given the process pattern return the matching processes and hosts.

        :param process_pattern: process pattern from the args or None
        :return: dict mapping tuple(hostname1,hostname2,...) -> [process name list]
        """
        raise NotImplemented


class AnsibleService(ServiceBase):
    """Service that is controlled via the ansible 'service' module"""

    @property
    def service_name(self):
        """Override if different"""
        return self.name

    def execute_action(self, action, host_pattern=None, process_pattern=None):
        if host_pattern:
            self.environment.inventory_manager.subset(self.inventory_groups)
            hosts = self.environment.inventory_manager.get_hosts(host_pattern)
            if not hosts:
                raise NoHostsMatch

        host_pattern = host_pattern or ','.join(self.inventory_groups)

        if action == 'status':
            command = 'service {} status'.format(self.service_name)
            return self._run_ansible_module(host_pattern, 'shell', command)

        service_args = 'name={} state={}'.format(self.service_name, STATES[action])
        return self._run_ansible_module(host_pattern, 'service', service_args)


class MultiAnsibleService(SubServicesMixin, AnsibleService):
    """Service that is made up of multiple other services e.g. RiakCS"""

    @abstractproperty
    def service_process_mapping(self):
        """
        Return a mapping of service names (as passed in by the user) to
        a tuple of (Linux service name, inventory group)
        """
        raise NotImplementedError

    @property
    def inventory_groups(self):
        return [
            inventory_group
            for service, inventory_group in self.service_process_mapping.values()
        ]

    @property
    def managed_services(self):
        return [name for name in self.service_process_mapping]

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

        non_zero_exits = []
        ran = False
        for service, run_on in self._get_service_host_groups(process_pattern):
            hosts = self.environment.inventory_manager.get_hosts(run_on)
            run_on = ','.join([host.name for host in hosts]) if host_pattern else run_on
            if hosts:
                ran = True
                exit_code = action_fn(service, run_on)
                if exit_code != 0:
                    non_zero_exits.append(exit_code)

        if not ran:
            raise NoHostsMatch
        return non_zero_exits[0] if non_zero_exits else 0

    def _get_service_host_groups(self, process_pattern):
        service_groups = []
        if process_pattern:
            for name in process_pattern.split(','):
                service_groups.append(self.service_process_mapping[name])
        else:
            service_groups = list(self.service_process_mapping.values())
        return service_groups


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
    service_process_mapping = {
        'riak': ('riak', 'riakcs'),
        'riakcs': ('riak-cs', 'riakcs'),
        'stanchion': ('stanchion', 'stanchion'),
    }


class Kafka(MultiAnsibleService):
    name = 'kafka'
    service_process_mapping = {
        'kafka': ('kafka-server', 'kafka'),
        'zookeeper': ('zookeeper', 'zookeeper')
    }


class Postgresql(MultiAnsibleService):
    name = 'postgresql'
    service_process_mapping = {
        'postgres': ('postgresql', 'postgresql,pg_standby'),
        'pgbouncer': ('pgbouncer', 'postgresql,pg_standby')
    }


class SingleSupervisorService(SupervisorService):
    """Single service that is managed by supervisor"""
    managed_services = []

    @abstractproperty
    def supervisor_process_name(self):
        """Supervisor process name for this service"""
        raise NotImplementedError

    def _get_processes_by_host(self, process_pattern=None):
        if not self.all_service_hosts:
            raise NoHostsMatch

        return {
            tuple(self.all_service_hosts): [self.supervisor_process_name]
        }


class CommCare(SingleSupervisorService):
    name = 'commcare'
    inventory_groups = ['webworkers', 'celery', 'pillowtop', 'touchforms', 'formplayer', 'proxy']

    @property
    def supervisor_process_name(self):
        return ''  # control all supervisor processes


class Webworker(SingleSupervisorService):
    name = 'webworker'
    inventory_groups = ['webworkers']

    @property
    def supervisor_process_name(self):
        return get_django_webworker_name(self.environment)


class Formplayer(SingleSupervisorService):
    name = 'formplayer'
    inventory_groups = ['formplayer']

    @property
    def supervisor_process_name(self):
        return get_formplayer_spring_instance_name(self.environment)


class Touchforms(SingleSupervisorService):
    name = 'touchforms'
    inventory_groups = ['touchforms']

    @property
    def supervisor_process_name(self):
        return get_formplayer_instance_name(self.environment)


class Celery(SupervisorService):
    name = 'celery'
    inventory_groups = ['celery']

    def _get_processes_by_host(self, process_pattern=None):
        return get_processes_by_host(
            self.all_service_hosts,
            get_celery_workers(self.environment),
            process_pattern
        )

    @property
    def managed_services(self):
        return get_managed_service_options(get_celery_workers(self.environment))


class Pillowtop(SupervisorService):
    name = 'pillowtop'
    inventory_groups = ['pillowtop']

    @property
    def managed_services(self):
        return get_managed_service_options(get_pillowtop_processes(self.environment))

    def _get_processes_by_host(self, process_pattern=None):
        return get_processes_by_host(
            self.all_service_hosts,
            get_pillowtop_processes(self.environment),
            process_pattern
        )


def get_managed_service_options(process_descriptors):
    """
    :param process_descriptors: List of ``ProcessDescriptor`` tuples
    :return:
    """
    options = defaultdict(set)
    for host, short_name, number, full_name in process_descriptors:
        options[short_name].add(number)
    return sorted([
        '{}{}'.format(name, ':[0-{}]'.format(max(numbers)) if len(numbers) > 1 else '')
        for name, numbers in options.items()
    ])


class ProcessMatcher(object):
    """Test a ``ProcessDescriptor`` for matching name and number combination."""
    def __init__(self, name, number=None):
        self.name = name
        self.number = number

    def __call__(self, process_descriptor):
        return (
            process_descriptor.short_name == self.name
            and (not self.number or process_descriptor.number == self.number)
        )


def get_processes_by_host(all_hosts, process_descriptors, process_pattern=None):
    """
    :param all_hosts: Filtered list of host names that should be considered.
    :param process_descriptors: List of ``ProcessDescriptor`` tuples
    :param process_pattern: Pattern to use to match processes against.
    :return: dict mapping tuple(hostname1,hostname2,...) -> [process name list]
    """
    matchers = []
    if process_pattern:
        for pattern in process_pattern.split(','):
            if ':' in pattern:
                name, num = pattern.split(':')
                matchers.append(ProcessMatcher(name, int(num)))
            else:
                matchers.append(ProcessMatcher(pattern))

    processes_by_host = defaultdict(set)
    for pd in process_descriptors:
        matches_pattern = not matchers or any(matcher(pd) for matcher in matchers)
        if pd.host in all_hosts and matches_pattern:
            processes_by_host[pd.host].add(pd.full_name)

    # convert to list so that we can sort
    processes_by_host = {
        host: list(p) for host, p in processes_by_host.items()
    }

    processes_by_hosts = {}
    # group hosts together so we do less calls to ansible
    items = sorted(processes_by_host.items(), key=lambda hp: hp[1])
    for processes, group in groupby(items, key=lambda hp: hp[1]):
        hosts = tuple([host_processes[0] for host_processes in group])
        processes_by_hosts[hosts] = processes
    return processes_by_hosts


SERVICES = [
    Postgresql,
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
    CommCare,
    Pillowtop,
]

SERVICE_NAMES = sorted([
    service.name for service in SERVICES
])

SERVICES_BY_NAME = {
    service.name: service for service in SERVICES
}


def validate_pattern(pattern):
    match = re.match(r'^[\w]+(:[\d]+)?(?:,[\w]+(:[\d]+)?)*$', pattern)
    if not match:
        raise ValueError
    return pattern


class Service(CommandBase):
    command = 'service'
    help = (
        "Manage services.\n"
        "Usage examples:"
        "   cchq <env> service postgresql status\n"
        "   cchq <env> service riakcs restart --only riak,riakcs\n"
        "   cchq <env> service celery help\n"
        "   cchq <env> service celery restart --limit <host>\n"
        "   cchq <env> service celery restart --only <queue-name>,<queue-name>:<queue_num>\n"
        "   cchq <env> service pillowtop restart --limit <host> --only <pillow-name>\n"
        "\n"
    )

    arguments = (
        Argument(
            'services',
            nargs="+",
            choices=SERVICE_NAMES,
            help="The services to run the command on"
        ),
        Argument(
            'action', choices=ACTIONS,
            help="What action to take"
        ),
        Argument('--limit', help=(
            "Restrict the hosts to run the command on."
            "\nUse 'help' action to list all options."
        ), include_in_docs=False),
        Argument('--only', type=validate_pattern, dest='process_pattern', help=(
            "Sub-service name to limit action to."
            "\nFormat as 'name' or 'name:number'."
            "\nUse 'help' action to list all options."
        )),
    )

    def run(self, args, unknown_args):
        environment = get_environment(args.env_name)

        services = [
            SERVICES_BY_NAME[name]
            for name in args.services
        ]

        ansible_context = AnsibleContext(args)
        non_zero_exits = []
        for service_cls in services:
            service = service_cls(environment, ansible_context)
            exit_code = service.run(args.action, args.limit, args.process_pattern)
            if exit_code != 0:
                non_zero_exits.append(exit_code)
        return non_zero_exits[0] if non_zero_exits else 0
