from __future__ import print_function

import os

import yaml
from parameterized import parameterized

from commcare_cloud.environment.main import Environment
from commcare_cloud.environment.paths import DefaultPaths

from nose.tools import assert_equal

TEST_ENVIRONMENTS_DIR = os.path.join(os.path.dirname(__file__), 'postgresql_config')
TEST_ENVIRONMENTS = os.listdir(TEST_ENVIRONMENTS_DIR)


@parameterized(TEST_ENVIRONMENTS)
def test_postgresql_config(env_name):
    env = Environment(DefaultPaths(env_name, environments_dir=TEST_ENVIRONMENTS_DIR))

    with open(env.paths.generated_yml) as f:
        generated = yaml.safe_load(f)
        assert generated.keys() == ['postgresql_dbs']

    expected_json = generated['postgresql_dbs']

    actual_json = env.postgresql_config.to_generated_variables(env)['postgresql_dbs']

    assert_equal(actual_json, expected_json)
