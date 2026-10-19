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


class FakeMonit:
    """Controls the state of tests/test_deploy/fake-monit-bin/monit"""

    def __init__(self, path):
        self.state_file = path / "state.json"

    def set_processes(self, **statuses):
        with open(self.state_file, "w") as fh:
            json.dump(statuses, fh)
