import os

from unittest.mock import patch
from nose.tools import assert_equal, assert_raises
from parameterized import parameterized

from commcare_cloud.commands.inventory_lookup.getinventory import (
    HostMatchException, HostPattern, get_server_address, split_host_group)

TEST_ENV_DIR = os.path.join(os.path.dirname(__file__), 'test_envs')


@parameterized([
    ("control", HostPattern(None, "control", None)),
    ("control[0]", HostPattern(None, "control", 0)),
    ("user@control[0]", HostPattern("user@", "control", 0)),
    ("user@control:3", HostPattern("user@", "control:3", None)),
    ("control:3", HostPattern(None, "control:3", None)),
    ("192.168.3.1", HostPattern(None, "192.168.3.1", None)),
    ("user@192.168.3.1", HostPattern("user@", "192.168.3.1", None)),
])
def test_split_host_group(pattern, expected):
    assert_equal(split_host_group(pattern), expected)


@parameterized([
    ("pgsynclog", "10.247.164.70"),
    ("postgresql[0]", "10.247.164.70"),
    ("user@postgresql[3]", "user@10.247.164.20"),
    ("user@postgresql:3", "user@10.247.164.20"),
    ("postgresql:3", "10.247.164.20"),
    ("192.168.3.1", "192.168.3.1"),
    ("user@192.168.3.1", "user@192.168.3.1"),
])
@patch('commcare_cloud.environment.paths.ENVIRONMENTS_DIR', TEST_ENV_DIR)
def test_get_server_address(pattern, expected):
    address = get_server_address("2018-04-04-icds-new-snapshot", pattern)
    assert_equal(address, expected)


@parameterized([
    ("postgresql:a",),
    ("postgresql[a]",),
    ("postgresql",),
    ("pgsynclog[1]",),
])
@patch('commcare_cloud.environment.paths.ENVIRONMENTS_DIR', TEST_ENV_DIR)
def test_get_server_address_errors(pattern):
    with assert_raises(HostMatchException):
        get_server_address("2018-04-04-icds-new-snapshot", pattern)


@patch('commcare_cloud.environment.paths.ENVIRONMENTS_DIR', TEST_ENV_DIR)
def test_get_server_address_with_groups():
    address = get_server_address("2018-04-04-icds-new-snapshot", "postgresql", allow_multiple=True)
    assert_equal(address, "\n".join([
        "10.247.164.26 - pgmain, postgresql, all",
        "10.247.164.20 - pgshard1, postgresql, all",
        "10.247.164.21 - pgshard2, postgresql, all",
        "10.247.164.64 - pgshard3, postgresql, all",
        "10.247.164.65 - pgshard4, postgresql, all",
        "10.247.164.66 - pgshard5, postgresql, all",
        "10.247.164.70 - pgsynclog, postgresql, all",
        "10.247.164.25 - pgucr, postgresql, all",
        "10.247.164.56 - plproxy1, postgresql, all",
    ]))


@patch('commcare_cloud.environment.paths.ENVIRONMENTS_DIR', TEST_ENV_DIR)
def test_get_server_address_for_monolith_with_groups():
    address = get_server_address("small_cluster", "all", allow_multiple=True)
    assert_equal(address, "\n".join([
        (
            "172.19.3.0 - demo_server0, proxy, webworkers, couchdb2_proxy, "
            "formplayer, shared_dir_host, control, mailrelay, django_manage, "
            "kafka, elasticsearch, couchdb2, all"
        ),
        (
            "172.19.3.1 - demo_server1, postgresql, redis, zookeeper, "
            "rabbitmq, kafka, elasticsearch, couchdb2, all"
        ),
        "172.19.3.2 - demo_server2, celery, all",
        "172.19.3.3 - demo_server3, pg_standby, pillowtop, couchdb2, all",
    ]))
