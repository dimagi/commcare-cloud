from __future__ import absolute_import, print_function, unicode_literals

import difflib
import os
from io import open
from unittest import SkipTest

import yaml
from nose.tools import assert_equal
from parameterized import parameterized

from commcare_cloud.environment.main import Environment
from commcare_cloud.environment.paths import DefaultPaths
from commcare_cloud.yaml import PreserveUnsafeDumper

TEST_ENVIRONMENTS_DIR = os.path.join(os.path.dirname(__file__), 'test_envs')
TEST_ENVIRONMENTS = os.listdir(TEST_ENVIRONMENTS_DIR)


@parameterized(TEST_ENVIRONMENTS)
def test_postgresql_config(env_name):
    # To update test configs when they get outdated:
    # python tests/test_postgresql_config.py

    env = Environment(DefaultPaths(env_name, environments_dir=TEST_ENVIRONMENTS_DIR))

    if not os.path.exists(env.paths.generated_yml):
        raise SkipTest

    with open(env.paths.generated_yml, encoding='utf-8') as f:
        generated = yaml.safe_load(f)
        assert list(generated.keys()) == ['postgresql_dbs']

    expected_json = generated['postgresql_dbs']

    actual_json = env.postgresql_config.to_generated_variables(env)['postgresql_dbs']

    assert_equal(actual_json, expected_json, msg=(
        '\n\n' +
        '\n'.join(difflib.unified_diff(
            list(yaml.dump(actual_json, Dumper=PreserveUnsafeDumper).splitlines()),
            list(yaml.dump(expected_json, Dumper=PreserveUnsafeDumper).splitlines()),
            'Actual',
            'Expected',
            lineterm=''
        ))
    ))


def update_configs():
    for env_name in TEST_ENVIRONMENTS:
        env = Environment(DefaultPaths(env_name, environments_dir=TEST_ENVIRONMENTS_DIR))
        if os.path.exists(env.paths.generated_yml):
            print("updating config:", env_name)
            update_config(env)


def update_config(env):
    json_data = env.postgresql_config.to_generated_variables(env)['postgresql_dbs']
    with open(env.paths.generated_yml, "w", encoding="utf-8") as fh:
        fh.write(yaml.dump(
            {"postgresql_dbs": json_data},
            Dumper=PreserveUnsafeDumper,
        ))


if __name__ == "__main__":
    update_configs()
