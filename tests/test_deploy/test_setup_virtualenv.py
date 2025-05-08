import os
import shutil
from pathlib import Path
from unittest import TestCase
from unittest.mock import patch

from testil import tempdir

from .. import ansible
from ..utils import set_log_level, test_context

PYTHON_VERSION = "3.9"


class TestSetupVirtualenv(TestCase):

    @classmethod
    def setUpClass(cls):
        test_context(cls, set_log_level("datadog"))
        cls.tmp = tmp = Path(test_context(cls, tempdir()))
        cls.previous_release = prev = tmp / "prev"
        cls.requires = tmp / "requires.txt"
        with open(cls.requires, mode="w"):
            pass
        fake_venv_bin = create_fake_virtualenv(prev / f"venv-{PYTHON_VERSION}")
        test_context(cls, patch.dict('os.environ', {"PATH": f"{fake_venv_bin}:{os.environ['PATH']}"}))

    def setUp(self):
        self.release = self.tmp / "release"
        (self.release / "requirements").mkdir(parents=True)
        (self.release / "requirements/prod-requirements.txt").symlink_to(self.requires)
        self.addCleanup(shutil.rmtree, self.release)

    def test_setup_virtualenv(self):
        result = ansible.run("setup_virtualenv", {
            "src": str(self.previous_release),
            "dest": str(self.release),
            "env_name": "venv",
            "python_version": PYTHON_VERSION,
        })
        self.assertTrue(result.get("changed"), result)
        assert (self.release / "venv-3.9/bin").is_dir(), listdir(self.release)
        assert (self.release / "venv/bin").is_dir(), listdir(self.release)
        self.assertEqual(result["venv"], str(self.release / "venv"))

    def test_setup_virtualenv_with_wrong_python_version(self):
        py36_release = self.tmp / "py36"
        create_fake_virtualenv(py36_release / "venv-3.6")
        with self.assertRaisesRegex(ansible.Fail, "virtualenv not found: "):
            ansible.run("setup_virtualenv", {
                "src": str(py36_release),
                "dest": str(self.release),
                "env_name": "venv",
                "python_version": PYTHON_VERSION,
            })
        assert not (self.release / "venv-3.6").is_dir()
        assert not (self.release / "venv-3.9").is_dir()
        assert not (self.release / "venv").is_dir()

    def test_failed_virtualenv_clone(self):
        setup_virtualenv = ansible.import_module("setup_virtualenv")
        with patch.object(setup_virtualenv, "clone_virtualenv") as mock:
            def clone_fail(prev_env, next_env, module):
                next_env.mkdir()
                raise Fail()
            mock.side_effect = clone_fail
            with self.assertRaises(Fail):
                ansible.run(setup_virtualenv, {
                    "src": str(self.previous_release),
                    "dest": str(self.release),
                    "env_name": "venv",
                    "python_version": PYTHON_VERSION,
                })
        assert not (self.release / "venv-3.9/bin/python").exists()
        assert not (self.release / "venv").exists(), listdir(self.release)
        self.test_setup_virtualenv()

    def test_failed_pip_sync(self):
        setup_virtualenv = ansible.import_module("setup_virtualenv")
        with patch.object(setup_virtualenv, "pip_sync") as mock:
            def pip_fail(dest, next_env, module, proxy):
                raise Fail()
            mock.side_effect = pip_fail
            with self.assertRaises(Fail):
                ansible.run(setup_virtualenv, {
                    "src": str(self.previous_release),
                    "dest": str(self.release),
                    "env_name": "venv",
                    "python_version": PYTHON_VERSION,
                })
        assert (self.release / "venv-3.9/bin/python").exists()
        assert not (self.release / "venv").exists(), listdir(self.release)
        with patch.object(setup_virtualenv, "clone_virtualenv") as mock:
            mock.side_effect = Fail("unexpected: env already created")
            self.test_setup_virtualenv()

    def test_setup_virtualenv_with_default_env_name(self):
        prev_venv = self.previous_release / f"python_env-{PYTHON_VERSION}"
        create_fake_virtualenv(prev_venv)
        self.addCleanup(shutil.rmtree, prev_venv)
        result = ansible.run("setup_virtualenv", {
            "src": str(self.previous_release),
            "dest": str(self.release),
            "python_version": PYTHON_VERSION,
        })
        self.assertTrue(result.get("changed"), result)
        assert (self.release / "python_env-3.9/bin").is_dir(), listdir(self.release)
        assert (self.release / "python_env/bin").is_dir(), listdir(self.release)
        self.assertEqual(result["venv"], str(self.release / "python_env"))

    def test_check_mode(self):
        result = ansible.run("setup_virtualenv", {
            "src": str(self.previous_release),
            "dest": str(self.release),
            "env_name": "venv",
            "python_version": PYTHON_VERSION,
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
