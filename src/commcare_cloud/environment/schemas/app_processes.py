from __future__ import print_function

from collections import Counter, namedtuple

import jsonobject


IpAddressProperty = jsonobject.StringProperty
IpAddressAndPortProperty = jsonobject.StringProperty
PortProperty = jsonobject.IntegerProperty
MemorySpecProperty = jsonobject.StringProperty
CommaSeparatedStrings = jsonobject.StringProperty


class CeleryOptions(jsonobject.JsonObject):
    _allow_dynamic_properties = False
    concurrency = jsonobject.IntegerProperty(default=1)
    pooling = jsonobject.StringProperty(choices=['gevent', 'prefork'], default='prefork')
    max_tasks_per_child = jsonobject.IntegerProperty(default=50)
    num_workers = jsonobject.IntegerProperty(default=1)
    optimize = jsonobject.BooleanProperty(default=False)


class AppProcessesConfig(jsonobject.JsonObject):
    _allow_dynamic_properties = False
    django_bind = IpAddressProperty()
    django_port = PortProperty()
    flower_port = PortProperty()
    gunicorn_workers_factor = jsonobject.IntegerProperty()
    gunicorn_workers_static_factor = jsonobject.IntegerProperty()
    jython_memory = MemorySpecProperty()
    formplayer_memory = MemorySpecProperty()
    http_proxy = IpAddressAndPortProperty()
    newrelic_djangoagent = jsonobject.BooleanProperty()
    newrelic_javaagent = jsonobject.BooleanProperty()
    django_command_prefix = jsonobject.StringProperty()
    celery_command_prefix = jsonobject.StringProperty()
    datadog_pythonagent = jsonobject.BooleanProperty()
    additional_no_proxy_hosts = CommaSeparatedStrings()

    service_blacklist = jsonobject.ListProperty(unicode)
    celery_processes = jsonobject.DictProperty(jsonobject.DictProperty(CeleryOptions))
    pillows = jsonobject.DictProperty(jsonobject.DictProperty())

    def check(self):
        validate_app_processes_config(self)

    def check_and_translate_hosts(self, environment):
        self.celery_processes = check_and_translate_hosts(environment, self.celery_processes)
        self.pillows = check_and_translate_hosts(environment, self.pillows)
        _validate_all_required_machines_mentioned(environment, self)

    def to_generated_variables(self):
        flower_host, = [machine for machine, queues_config in self.celery_processes.items()
                        if 'flower' in queues_config]
        return {
            'CELERY_FLOWER_URL': "http://{flower_host}:5555".format(flower_host=flower_host),
            'app_processes_config': self.to_json(),
            'celery_queues': CELERY_PROCESS_NAMES
        }


class CeleryProcess(namedtuple('CeleryProcess', ['name', 'required'])):
    def __new__(cls, name, required=True, *args, **kwargs):
        return super(CeleryProcess, cls).__new__(cls, name, required, *args, **kwargs)


CELERY_PROCESSES = [
    CeleryProcess("analytics_queue"),
    CeleryProcess("async_restore_queue", required=False),
    CeleryProcess("background_queue"),
    CeleryProcess("beat", required=False),
    CeleryProcess("case_rule_queue"),
    CeleryProcess("case_import_queue"),
    CeleryProcess("celery"),
    CeleryProcess("celery_periodic", required=False),
    CeleryProcess("email_queue"),
    CeleryProcess("export_download_queue"),
    CeleryProcess("flower"),
    CeleryProcess("icds_aggregation_queue", required=False),
    CeleryProcess("icds_dashboard_reports_queue", required=False),
    CeleryProcess("ils_gateway_sms_queue", required=False),
    CeleryProcess("logistics_background_queue", required=False),
    CeleryProcess("logistics_reminder_queue", required=False),
    CeleryProcess("reminder_case_update_queue"),
    CeleryProcess("reminder_queue", required=False),
    CeleryProcess("reminder_rule_queue"),
    CeleryProcess("repeat_record_queue"),
    CeleryProcess("saved_exports_queue"),
    CeleryProcess("sumologic_logs_queue", required=False),
    CeleryProcess("send_report_throttled", required=False),
    CeleryProcess("sms_queue", required=False), # TODO remove required
    CeleryProcess("submission_reprocessing_queue", required=False),
    CeleryProcess("ucr_indicator_queue", required=False),
    CeleryProcess("ucr_queue", required=False),
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
    assert not (app_processes_config.newrelic_djangoagent and app_processes_config.datadog_pythonagent), \
        'You cannot run NewRelic APM and Datadog APM'


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
    :param environment: name of the env used to lookup the inventory
    :param host_mapping: dictionary where keys can be one of:
                         * host (must be in inventory file)
                         * inventory group containing a single host
                         * 'None'
    :return: dictionary with the same content as the input but where
             keys that were inventory groups have been converted into their
             representative host
    """
    translated = {}
    for host, config in host_mapping.items():
        translated[environment.translate_host(host, environment.paths.app_processes_yml)] = config

    return translated
