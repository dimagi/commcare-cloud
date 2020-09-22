from __future__ import absolute_import
from __future__ import unicode_literals
import os

from mock import patch
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
