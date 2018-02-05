from __future__ import print_function

from collections import Counter

import jsonobject as jsonobject
import yaml
from commcare_cloud.environment import get_available_envs, get_app_processes_filepath, \
    get_default_app_processes_filepath
from parameterized import parameterized


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


CELERY_PROCESS_NAMES = [
    "async_restore_queue",
    "background_queue",
    "celery",
    "celery_periodic",
    "email_queue",
    "enikshay_queue",
    "flower",
    "ils_gateway_sms_queue",
    "logistics_background_queue",
    "logistics_reminder_queue",
    "pillow_retry_queue",
    "reminder_case_update_queue",
    "reminder_queue",
    "reminder_rule_queue",
    "repeat_record_queue",
    "saved_exports_queue",
    "sms_queue",
    "submission_reprocessing_queue",
    "ucr_indicator_queue",
    "ucr_queue",
]


OPTIONAL_CELERY_PROCESSES = [
    'celery_periodic',
    'enikshay_queue',
    'ils_gateway_sms_queue',
    'logistics_background_queue',
    'logistics_reminder_queue',
    'reminder_queue',
    'submission_reprocessing_queue',
    'ucr_indicator_queue',
]


@parameterized(get_available_envs())
def test_app_processes_yml(env):
    with open(get_default_app_processes_filepath()) as f:
        app_processes_json = yaml.load(f)
    with open(get_app_processes_filepath(env)) as f:
        app_processes_json.update(yaml.load(f))

    app_processes_config = AppProcessesConfig.wrap(app_processes_json)
    all_queues_mentioned = Counter({queue_name: 0 for queue_name in CELERY_PROCESS_NAMES})
    for machine, queues_config in app_processes_config.celery_processes.items():
        for comma_separated_queue_names, celery_options in queues_config.items():
            queue_names = comma_separated_queue_names.split(',')
            if 'flower' in queue_names:
                assert len(queue_names) == 1, \
                    "The special 'flower' process may not be grouped with other processes"
            for queue_name in queue_names:
                assert queue_name in CELERY_PROCESS_NAMES,\
                    "Celery process not recognized: {}".format(queue_name)
            all_queues_mentioned.update(queue_names)
    required_but_not_mentioned = [queue_name for queue_name, count in all_queues_mentioned.items()
                                  if count == 0 and queue_name not in OPTIONAL_CELERY_PROCESSES]
    assert len(required_but_not_mentioned) == 0, \
        "The following queues were not mentioned: {}".format(', '.join(required_but_not_mentioned))
    assert all_queues_mentioned['celery_periodic'] <= 1, \
        'You cannot run the periodic celery queue on more than one machine because it implies celery beat.'
