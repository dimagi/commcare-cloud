from __future__ import print_function

from parameterized import parameterized

from commcare_cloud.environment.main import get_environment
from commcare_cloud.environment.paths import get_available_envs


@parameterized(get_available_envs())
def test_meta_yml(env):
    environment = get_environment(env)
    environment.meta_config  # check if the schema wraps it


@parameterized(get_available_envs())
def test_app_processes_yml(env):
    environment = get_environment(env)
    environment.app_processes_config.check()
    environment.translated_app_processes_config.check()


@parameterized(get_available_envs())
def test_fab_settings_yml(env):
    environment = get_environment(env)
    environment.fab_settings_config  # check if the schema wraps it
