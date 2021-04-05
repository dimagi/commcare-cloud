from __future__ import print_function

from __future__ import absolute_import
from __future__ import unicode_literals
from collections import Counter, namedtuple

import jsonobject
from clint.textui import puts, indent

from commcare_cloud.colors import color_warning
import six

IpAddressProperty = jsonobject.StringProperty
IpAddressAndPortProperty = jsonobject.StringProperty
PortProperty = jsonobject.IntegerProperty
MemorySpecProperty = jsonobject.StringProperty
CommaSeparatedStrings = jsonobject.StringProperty


class CeleryOptions(jsonobject.JsonObject):
    _allow_dynamic_properties = False
    concurrency = jsonobject.IntegerProperty(default=1)
    pooling = jsonobject.StringProperty(choices=['gevent', 'prefork'], default='prefork')
    max_tasks_per_child = jsonobject.IntegerProperty(default=None)
    num_workers = jsonobject.IntegerProperty(default=1)
    optimize = jsonobject.BooleanProperty(default=False)


class PillowOptions(jsonobject.JsonObject):
    _allow_dynamic_properties = False
    start_process = jsonobject.IntegerProperty(default=0)
    num_processes = jsonobject.IntegerProperty(default=1)
    dedicated_migration_process = jsonobject.BooleanProperty(default=False)
    total_processes = jsonobject.IntegerProperty(default=None, exclude_if_none=True)
    processor_chunk_size = jsonobject.IntegerProperty(default=None, exclude_if_none=True)


class AppProcessesConfig(jsonobject.JsonObject):
    _allow_dynamic_properties = False
    django_bind = IpAddressProperty()
    django_port = PortProperty()
    flower_port = PortProperty()
    gunicorn_workers_factor = jsonobject.IntegerProperty()
    gunicorn_workers_static_factor = jsonobject.IntegerProperty()
    formplayer_memory = MemorySpecProperty()
    formplayer_maxmetaspacesize = MemorySpecProperty()
    formplayer_g1heapregionsize = MemorySpecProperty()
    http_proxy = IpAddressAndPortProperty()
    django_command_prefix = jsonobject.StringProperty()
    celery_command_prefix = jsonobject.StringProperty()
    formplayer_command_args = jsonobject.StringProperty()
    datadog_pythonagent = jsonobject.BooleanProperty()
    additional_no_proxy_hosts = CommaSeparatedStrings()

    service_blacklist = jsonobject.ListProperty(six.text_type)
    management_commands = jsonobject.DictProperty(jsonobject.DictProperty())
    celery_processes = jsonobject.DictProperty(jsonobject.DictProperty(CeleryOptions))
    pillows = jsonobject.DictProperty(jsonobject.DictProperty(PillowOptions))

    celery_heartbeat_thresholds = jsonobject.DictProperty(int)

    def check(self):
        validate_app_processes_config(self)

    def check_and_translate_hosts(self, environment):
        self.management_commands = check_and_translate_hosts(environment, self.management_commands)
        self.celery_processes = check_and_translate_hosts(environment, self.celery_processes)
        self.pillows = check_and_translate_hosts(environment, self.pillows)
        self.pillows = filter_out_deprecated_pillows(environment, self.pillows)
        _validate_all_required_machines_mentioned(environment, self)

    def get_celery_heartbeat_thresholds(self):
        for process in self.celery_heartbeat_thresholds:
            assert process in CELERY_PROCESS_NAMES, '"{}" is not a recognised celery process'.format(process)

        celery_queues = set()
        for host, celery_options in self.celery_processes.items():
            if host == 'None':
                continue
            for process_group in celery_options.keys():
                celery_queues.update(process_group.split(','))

        return {
            p.name: self.celery_heartbeat_thresholds.get(p.name, p.blockage_threshold) for p in CELERY_PROCESSES
            if p.is_queue and p.name in celery_queues
        }

    def to_generated_variables(self):
        flower_host, = [machine for machine, queues_config in self.celery_processes.items()
                        if 'flower' in queues_config]
        return {
            'CELERY_FLOWER_URL': "http://{flower_host}:5555".format(flower_host=flower_host),
            'app_processes_config': self.to_json(),
            'celery_queues': CELERY_PROCESS_NAMES,
            'CELERY_HEARTBEAT_THRESHOLDS': self.get_celery_heartbeat_thresholds()
        }


class CeleryProcess(namedtuple('CeleryProcess', ['name', 'required', 'is_queue', 'blockage_threshold'])):
    def __new__(cls, name, required=True, is_queue=True, blockage_threshold=None,
                *args, **kwargs):
        return super(CeleryProcess, cls).__new__(cls, name, required, is_queue, blockage_threshold,
                                                 *args, **kwargs)


CELERY_PROCESSES = [
    CeleryProcess("analytics_queue", blockage_threshold=30 * 60),
    CeleryProcess("async_restore_queue", required=False, blockage_threshold=60),
    CeleryProcess("background_queue", blockage_threshold=10 * 60),
    CeleryProcess("beat", required=False, is_queue=False),
    CeleryProcess("case_rule_queue", blockage_threshold=60 * 60),
    CeleryProcess("case_import_queue", blockage_threshold=60),
    CeleryProcess("celery", blockage_threshold=60),
    CeleryProcess("celery_periodic", required=False, blockage_threshold=10 * 60),
    CeleryProcess("dashboard_comparison_queue", required=False),
    CeleryProcess("email_queue", blockage_threshold=30),
    CeleryProcess("export_download_queue", blockage_threshold=30),
    CeleryProcess("flower", is_queue=False),
    CeleryProcess("icds_aggregation_queue", required=False),
    CeleryProcess("icds_dashboard_reports_queue", required=False),
    CeleryProcess("logistics_background_queue", required=False),
    CeleryProcess("logistics_reminder_queue", required=False),
    CeleryProcess("reminder_case_update_queue", blockage_threshold=15 * 60),
    CeleryProcess("reminder_queue", required=False, blockage_threshold=15 * 60),
    CeleryProcess("reminder_rule_queue", blockage_threshold=15 * 60),
    CeleryProcess("repeat_record_queue", blockage_threshold=60 * 60),
    CeleryProcess("saved_exports_queue", blockage_threshold=6 * 60 * 60),
    CeleryProcess("sumologic_logs_queue", required=False, blockage_threshold=6 * 60 * 60),
    CeleryProcess("send_report_throttled", required=False, blockage_threshold=6 * 60 * 60),
    CeleryProcess("sms_queue", required=False, blockage_threshold=5 * 60), # TODO remove required
    CeleryProcess("submission_reprocessing_queue", required=False, blockage_threshold=60 * 60),
    CeleryProcess("ucr_indicator_queue", required=False, blockage_threshold=60 * 60),
    CeleryProcess("ucr_queue", required=False, blockage_threshold=60 * 60),
    CeleryProcess("user_import_queue", required=False, blockage_threshold=60 * 60),
    CeleryProcess("ush_background_tasks", required=False, blockage_threshold=3 * 60 * 60)
]


CELERY_PROCESS_NAMES = [process.name for process in CELERY_PROCESSES]
OPTIONAL_CELERY_PROCESSES = [process.name for process in CELERY_PROCESSES
                             if not process.required]

# queues specified in solo_queues cannot be combined with other queues in the same process
SOLO_QUEUES = [
    # because these don't actually run normal celery processes
    'flower', 'beat',
    # because these run management commands in addition to normal celery processes
    # (see commcare_cloud/ansible/roles/commcarehq/tasks/celery.yml)
    'reminder_queue', 'submission_reprocessing_queue', 'sms_queue',
]


def validate_app_processes_config(app_processes_config):
    all_queues_mentioned = Counter({queue_name: 0 for queue_name in CELERY_PROCESS_NAMES})
    for machine, queues_config in app_processes_config.celery_processes.items():
        for comma_separated_queue_names, celery_options in queues_config.items():
            queue_names = comma_separated_queue_names.split(',')
            for queue_name in queue_names:
                if queue_name in SOLO_QUEUES:
                    assert len(queue_names) == 1, \
                        "The special process {} may not be grouped with other processes".format(queue_name)
                assert queue_name in CELERY_PROCESS_NAMES, \
                    "Celery process not recognized or has extra whitespace: {}".format(queue_name)
            all_queues_mentioned.update(queue_names)
    required_but_not_mentioned = [queue_name for queue_name, count in all_queues_mentioned.items()
                                  if count == 0 and queue_name not in OPTIONAL_CELERY_PROCESSES]
    assert len(required_but_not_mentioned) == 0, \
        "The following queues were not mentioned: {}".format(', '.join(required_but_not_mentioned))
    assert all_queues_mentioned['beat'] <= 1, \
        'You cannot run beat on more than one machine.'
    assert all_queues_mentioned['flower'] <= 1, \
        'You cannot run flower on more than one machine because CELERY_FLOWER_URL assumes one endpoint.'


def _validate_all_required_machines_mentioned(environment, translated_app_process_config):
    inventory = environment.inventory_manager
    for host in inventory.groups['pillowtop'].get_hosts():
        assert host.get_name() in translated_app_process_config.pillows, \
            "pillowtop machine {} not in {}".format(host.get_name(), environment.paths.app_processes_yml)

    for host in inventory.groups['celery'].get_hosts():
        assert host.get_name() in translated_app_process_config.celery_processes, \
            "celery machine {} not in {}".format(host.get_name(), environment.paths.app_processes_yml)


def check_and_translate_hosts(environment, host_mapping):
    """
    :param environment: the env used to lookup the inventory
    :param host_mapping: dictionary where keys can be one of:
                         * host (must be in inventory file)
                         * inventory group containing a single host
                         * 'None'
    :return: dictionary with the same content as the input but where
             keys that were inventory groups have been converted into their
             representative host
    """
    translated = {}
    for comma_separated_hosts, config in host_mapping.items():
        for host in comma_separated_hosts.split(','):
            translated[environment.translate_host(host, environment.paths.app_processes_yml)] = config

    return translated


def get_machine_alias(environment, host):
    """

    :param environment: the env used to lookup the inventory
    :param host: the inventory host (expressed as i.e. an ip address) to look up
    :return: the canonical group name for that host
    """
    for name, group in environment.inventory_manager.groups.items():
        if len(group.hosts) == 1 and group.hosts[0].name == host:
            return name
    return host


def filter_out_deprecated_pillows(environment, pillows):
    deprecated_pillows = ['GeographyFluffPillow', 'FarmerRecordFluffPillow']
    good_pillows = {}
    bad_pillows = set()
    for host, pillow_configs in pillows.items():
        good_pillows[host] = {}
        for pillow_name, pillow_config in pillow_configs.items():
            if pillow_name not in deprecated_pillows:
                good_pillows[host][pillow_name] = pillow_config
            else:
                bad_pillows.add(pillow_name)
    if bad_pillows:
        puts(color_warning(
            'This environment references deprecated pillow(s):\n'
        ))
        with indent():
            for pillow_name in sorted(bad_pillows):
                puts(color_warning('- {}'.format(pillow_name)))
        puts(color_warning(
            '\nThis pillows are unused and no longer needed.\n'
            'To get rid of this warning, remove those pillows from {}'
            .format(environment.paths.app_processes_yml)
        ))
    return good_pillows
