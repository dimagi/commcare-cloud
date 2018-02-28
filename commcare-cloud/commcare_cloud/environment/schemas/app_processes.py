from __future__ import print_function

from collections import Counter, namedtuple

import jsonobject

from commcare_cloud.environment.loaders import get_inventory

IpAddressProperty = jsonobject.StringProperty
IpAddressAndPortProperty = jsonobject.StringProperty
PortProperty = jsonobject.IntegerProperty
MemorySpecProperty = jsonobject.StringProperty
CommaSeparatedStrings = jsonobject.StringProperty


class CeleryOptions(jsonobject.JsonObject):
    _allow_dynamic_properties = False
    concurrency = jsonobject.IntegerProperty()
    pooling = jsonobject.StringProperty(choices=['gevent', 'prefork'], default='prefork')
    max_tasks_per_child = jsonobject.IntegerProperty()
    server_whitelist = IpAddressProperty()


class AppProcessesConfig(jsonobject.JsonObject):
    _allow_dynamic_properties = False
    environment = jsonobject.StringProperty()
    django_bind = IpAddressProperty()
    django_port = PortProperty()
    flower_port = PortProperty()
    gunicorn_workers_factor = jsonobject.IntegerProperty()
    gunicorn_workers_static_factor = jsonobject.IntegerProperty()
    jython_memory = MemorySpecProperty()
    formplayer_memory = MemorySpecProperty()
    http_proxy = IpAddressAndPortProperty()
    newrelic_javaagent = jsonobject.BooleanProperty()
    additional_no_proxy_hosts = CommaSeparatedStrings()

    service_blacklist = jsonobject.ListProperty(unicode)
    celery_processes = jsonobject.DictProperty(jsonobject.DictProperty(CeleryOptions))
    pillows = jsonobject.DictProperty(jsonobject.DictProperty())

    def check(self):
        validate_app_processes_config(self)

    def check_and_translate_hosts(self, env_name):
        self.celery_processes = check_and_translate_hosts(env_name, self.celery_processes)
        self.pillows = check_and_translate_hosts(env_name, self.pillows)


class CeleryProcess(namedtuple('CeleryProcess', ['name', 'required'])):
    def __new__(cls, name, required=True, *args, **kwargs):
        return super(CeleryProcess, cls).__new__(cls, name, required, *args, **kwargs)


CELERY_PROCESSES = [
    CeleryProcess("async_restore_queue"),
    CeleryProcess("background_queue"),
    CeleryProcess("case_rule_queue"),
    CeleryProcess("celery"),
    CeleryProcess("celery_periodic", required=False),
    CeleryProcess("email_queue"),
    CeleryProcess("enikshay_queue", required=False),
    CeleryProcess("flower"),
    CeleryProcess("ils_gateway_sms_queue", required=False),
    CeleryProcess("logistics_background_queue", required=False),
    CeleryProcess("logistics_reminder_queue", required=False),
    CeleryProcess("pillow_retry_queue"),
    CeleryProcess("reminder_case_update_queue"),
    CeleryProcess("reminder_queue", required=False),
    CeleryProcess("reminder_rule_queue"),
    CeleryProcess("repeat_record_queue"),
    CeleryProcess("saved_exports_queue"),
    CeleryProcess("send_report_throttled", required=False),
    CeleryProcess("sms_queue"),
    CeleryProcess("submission_reprocessing_queue", required=False),
    CeleryProcess("ucr_indicator_queue", required=False),
    CeleryProcess("ucr_queue"),
]


CELERY_PROCESS_NAMES = [process.name for process in CELERY_PROCESSES]
OPTIONAL_CELERY_PROCESSES = [process.name for process in CELERY_PROCESSES
                             if not process.required]


def validate_app_processes_config(app_processes_config):
    all_queues_mentioned = Counter({queue_name: 0 for queue_name in CELERY_PROCESS_NAMES})
    for machine, queues_config in app_processes_config.celery_processes.items():
        for comma_separated_queue_names, celery_options in queues_config.items():
            queue_names = comma_separated_queue_names.split(',')
            if 'flower' in queue_names:
                assert len(queue_names) == 1, \
                    "The special 'flower' process may not be grouped with other processes"
            for queue_name in queue_names:
                assert queue_name in CELERY_PROCESS_NAMES, \
                    "Celery process not recognized: {}".format(queue_name)
            all_queues_mentioned.update(queue_names)
    required_but_not_mentioned = [queue_name for queue_name, count in all_queues_mentioned.items()
                                  if count == 0 and queue_name not in OPTIONAL_CELERY_PROCESSES]
    assert len(required_but_not_mentioned) == 0, \
        "The following queues were not mentioned: {}".format(', '.join(required_but_not_mentioned))
    assert all_queues_mentioned['celery_periodic'] <= 1, \
        'You cannot run the periodic celery queue on more than one machine because it implies celery beat.'


def check_and_translate_hosts(env_name, host_mapping):
    """
    :param env_name: name of the env used to lookup the inventory
    :param host_mapping: dictionary where keys can be one of:
                         * host (must be in inventory file)
                         * inventory group containing a single host
                         * literal '*' or 'None'
    :return: dictionary with the same content as the input but where
             keys that were inventory groups have been converted into their
             representative host
    """
    translated = {}
    inventory = get_inventory(env_name)
    for host, config in host_mapping.items():
        if host == 'None' or host == '*' or host in inventory.hosts:
            translated[host] = config
        else:
            group = inventory.groups.get(host)
            assert group, 'Unknown host referenced in app processes: {}'.format(host)
            group_hosts = group.get_hosts()
            assert len(group_hosts) == 1, (
                'Unable to translate host referenced '
                'in app processes to a single host name: {}'.format(host))
            host = group_hosts[0].get_name()
            translated[host] = config

    return translated
