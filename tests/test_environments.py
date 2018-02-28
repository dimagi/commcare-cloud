from __future__ import print_function

import yaml
from parameterized import parameterized

from commcare_cloud.environment.paths import get_available_envs, \
    get_default_app_processes_filepath, get_app_processes_filepath
from commcare_cloud.environment.schemas.app_processes import AppProcessesConfig


@parameterized(get_available_envs())
def test_app_processes_yml(env):
    with open(get_default_app_processes_filepath()) as f:
        app_processes_json = yaml.load(f)
    with open(get_app_processes_filepath(env)) as f:
        app_processes_json.update(yaml.load(f))

    app_processes_config = AppProcessesConfig.wrap(app_processes_json)
    app_processes_config.check()
    app_processes_config.check_and_translate_hosts(env)
    app_processes_config.check()
