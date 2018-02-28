import yaml
from commcare_cloud.environment.paths import get_available_envs, get_default_app_processes_filepath, \
    get_app_processes_filepath
from nose_parameterized import parameterized

from utils import check_and_translate_hosts


@parameterized(get_available_envs())
def test_app_process_referenced_hosts(env_name):
    with open(get_default_app_processes_filepath()) as f:
        app_processes_json = yaml.load(f)
    with open(get_app_processes_filepath(env_name)) as f:
        app_processes_json.update(yaml.load(f))

    check_and_translate_hosts(env_name, app_processes_json['celery_processes'])
    check_and_translate_hosts(env_name, app_processes_json['pillows'])
