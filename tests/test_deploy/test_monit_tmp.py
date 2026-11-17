import json
import os
from pathlib import Path
from tempfile import TemporaryDirectory as tempdir
from unittest.mock import patch

import pytest
from unmagic import fixture

from .. import ansible
from ..utils import set_log_level

FAKE_MONIT_BIN = Path(__file__).parent / "fake-monit-bin"


@fixture
def fake_monit():
    with set_log_level("datadog"), tempdir() as tmp:
        monit = FakeMonit(Path(tmp))
        monit.set_processes()
        with patch.dict("os.environ", {
            "PATH": f"{FAKE_MONIT_BIN}:{os.environ['PATH']}",
            "FAKE_MONIT_STATE": str(monit.state_file),
        }):
            yield monit


@fake_monit
def test_not_configured():
    with pytest.raises(ansible.Fail, match="process not presently configured with monit"):
        ansible.run("monit_tmp", {"name": "postgresql_14", "state": "unmonitored"})


def test_unmonitor_running_process():
    monit = fake_monit()
    monit.set_processes(postgresql_14="OK")
    result = ansible.run("monit_tmp", {"name": "postgresql_14", "state": "unmonitored"})
    assert result["changed"] is True, result
    assert monit.changes() == ["unmonitor postgresql_14"]


def test_unmonitor_already_unmonitored():
    monit = fake_monit()
    monit.set_processes(postgresql_14="Not monitored")
    result = ansible.run("monit_tmp", {"name": "postgresql_14", "state": "unmonitored"})
    assert result["changed"] is False, result
    assert monit.changes() == []


def test_monitor_unmonitored_process():
    monit = fake_monit()
    monit.set_processes(postgresql_14="Not monitored")
    result = ansible.run("monit_tmp", {"name": "postgresql_14", "state": "monitored"})
    assert result["changed"] is True, result
    assert monit.changes() == ["monitor postgresql_14"]


def test_monitor_already_monitored():
    monit = fake_monit()
    monit.set_processes(postgresql_14="OK")
    result = ansible.run("monit_tmp", {"name": "postgresql_14", "state": "monitored"})
    assert result["changed"] is False, result
    assert monit.changes() == []


def test_check_mode():
    monit = fake_monit()
    monit.set_processes(postgresql_14="OK")
    result = ansible.run("monit_tmp", {
        "name": "postgresql_14",
        "state": "unmonitored",
        "_ansible_check_mode": True,
    })
    assert result["changed"] is True, result
    assert monit.changes() == []


class FakeMonit:
    """Controls the state of tests/test_deploy/fake-monit-bin/monit"""

    def __init__(self, path):
        self.state_file = path / "state.json"
        self.log_file = path / "commands.log"

    def set_processes(self, **statuses):
        with open(self.state_file, "w") as fh:
            json.dump(statuses, fh)

    def changes(self):
        """Return the logged commands that change process state"""
        with open(self.log_file) as fh:
            commands = fh.read().splitlines()
        return [c for c in commands if c.split()[0] in ("monitor", "unmonitor")]
