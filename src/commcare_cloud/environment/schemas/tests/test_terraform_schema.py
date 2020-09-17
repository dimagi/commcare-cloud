from __future__ import absolute_import
from commcare_cloud.environment.schemas.terraform import ServerConfig


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
