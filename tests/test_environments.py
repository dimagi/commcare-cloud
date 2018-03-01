from __future__ import print_function

import yaml
from parameterized import parameterized

from commcare_cloud.environment.main import get_environment
from commcare_cloud.environment.paths import get_available_envs, \
    get_default_app_processes_filepath, get_app_processes_filepath
from commcare_cloud.environment.schemas.app_processes import AppProcessesConfig


@parameterized(get_available_envs())
def test_app_processes_yml(env):
    environment = get_environment(env)
    environment.app_processes_config.check()
    environment.translated_app_processes_config.check()
