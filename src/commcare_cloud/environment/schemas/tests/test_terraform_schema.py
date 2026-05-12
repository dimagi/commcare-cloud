from nose.tools import assert_raises
from commcare_cloud.environment.schemas.terraform import (
    ServerConfig, RdsInstanceConfig, RdsParameterGroupConfig, RDS_DEFAULT_PARAMS,
)


def test_single_server():
    server_spec = ServerConfig.wrap({
        'server_name': 'server0-test',
        'os': 'bionic'
    })
    try:
        server_spec.get_host_group_name()
    except ValueError:
        pass
    except Exception:
        assert False, "Should raise a ValueError"
    else:
        assert False, "Should raise a ValueError"

    assert server_spec.get_all_server_names() == ['server0-test']
    assert server_spec.get_all_host_names() == ['server0']


def test_multi_server():
    server_spec = ServerConfig.wrap({
        'server_name': 'server_a{i}-test',
        'count': 2,
        'os': 'bionic',
    })
    assert server_spec.get_host_group_name() == 'server_a'
    assert server_spec.get_all_server_names() == ['server_a000-test', 'server_a001-test']
    assert server_spec.get_all_host_names() == ['server_a000', 'server_a001']


def test_rds_parameter_group_config():
    group = RdsParameterGroupConfig.wrap({
        'name': 'pg18-params-staging',
        'family': 'postgres18',
        'params': {
            'shared_preload_libraries': 'pg_stat_statements',
        },
    })
    assert group.name == 'pg18-params-staging'
    assert group.family == 'postgres18'
    assert group.params['shared_preload_libraries'] == 'pg_stat_statements'
    for param_name in RDS_DEFAULT_PARAMS:
        assert param_name in group.params, f"Default param {param_name} not applied"


def test_rds_instance_config():
    instance_with_params = RdsInstanceConfig.wrap(
        {
            "identifier": "pg0-staging",
            "instance_type": "db.t4g.large",
            "storage": 300,
            "params": {"shared_preload_libraries": "pg_stat_statements"},
        }
    )
    assert instance_with_params.parameter_group is None

    instance_with_param_group = RdsInstanceConfig.wrap({
        'identifier': 'pg0-staging',
        'instance_type': 'db.t4g.large',
        'storage': 300,
        'parameter_group': 'pg18-params-staging',
    })
    assert instance_with_param_group.parameter_group == 'pg18-params-staging'

    with assert_raises(ValueError) as context:
        RdsInstanceConfig.wrap({
            'identifier': 'pg0-staging',
            'instance_type': 'db.t4g.large',
            'storage': 300,
            # ensure mutually exclusive
            'parameter_group': 'pg18-params-staging',
            'params': {'shared_preload_libraries': 'pg_stat_statements'},
        })
    message = str(context.exception)
    assert 'pg0-staging' in message
    assert 'mutually exclusive' in message
