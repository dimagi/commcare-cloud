import os
import shutil
from pathlib import Path
from unittest import TestCase
from unittest.mock import patch

from testil import tempdir

from .. import ansible
from ..utils import set_log_level, test_context


class TestSetupVirtualenv(TestCase):

    @classmethod
    def setUpClass(cls):
        test_context(cls, set_log_level("datadog"))
        cls.tmp = tmp = Path(test_context(cls, tempdir()))
        cls.previous_release = prev = tmp / "prev"
        cls.requires = tmp / "requires.txt"
        with open(cls.requires, mode="w"):
            pass
        fake_venv_bin = create_fake_virtualenv(prev / "venv")
        test_context(cls, patch.dict('os.environ', {"PATH": f"{fake_venv_bin}:{os.environ['PATH']}"}))

    def setUp(self):
        self.release = self.tmp / "release"
        (self.release / "requirements").mkdir(parents=True)
        (self.release / "requirements/prod-requirements.txt").symlink_to(self.requires)
        self.addCleanup(shutil.rmtree, self.release)

    def test_setup_virtualenv(self):
        result = ansible.run("setup_virtualenv", {
            "dest": str(self.release),
            "env_name": "venv",
        })
        self.assertTrue(result.get("changed"), result)
        assert (self.release / "venv/bin").is_dir(), listdir(self.release)
        self.assertEqual(result["venv"], str(self.release / "venv"))

    def test_failed_uv_sync(self):
        def uv_sync(*args, **kwargs):
            raise Fail()

        setup_virtualenv = ansible.import_module("setup_virtualenv")
        with patch.object(setup_virtualenv, "uv_sync", uv_sync):
            with self.assertRaises(Fail):
                ansible.run(setup_virtualenv, {
                    "dest": str(self.release),
                    "env_name": "venv",
                })
        assert not (self.release / ".venv").exists(), listdir(self.release)
        assert not (self.release / "venv").exists(), listdir(self.release)

        self.test_setup_virtualenv()  # should not fail

    def test_setup_virtualenv_with_default_env_name(self):
        result = ansible.run("setup_virtualenv", {
            "dest": str(self.release),
        })
        self.assertTrue(result.get("changed"), result)
        assert (self.release / "python_env/bin").is_dir(), listdir(self.release)
        self.assertEqual(result["venv"], str(self.release / "python_env"))

    def test_check_mode(self):
        result = ansible.run("setup_virtualenv", {
            "dest": str(self.release),
            "env_name": "venv",
            "_ansible_check_mode": True,
        })
        assert not Path(result["venv"]).exists(), result
        assert not (self.release / "venv-3.9").exists(), result


def create_fake_virtualenv(path):
    fake_venv_bin = Path(__file__).parent / "fake-venv-bin"
    path.mkdir(parents=True)
    (path / "bin").symlink_to(fake_venv_bin)
    return fake_venv_bin


def listdir(path):
    return {p.name for p in path.iterdir()}


class Fail(Exception):
    pass
