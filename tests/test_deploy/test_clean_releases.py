import os
from datetime import datetime, timedelta
from hashlib import sha1
from pathlib import Path
from unittest import TestCase

from testil import tempdir

from .. import ansible
from ..utils import set_log_level, test_context


class TestCleanReleases(TestCase):

    @classmethod
    def setUpClass(cls):
        test_context(cls, set_log_level("datadog"))

    def setUp(self):
        self.releases = Path(test_context(self, tempdir()))
        self.release_names = names = []
        for i in range(4):
            name = f"r{i}"
            self.make_release(name)
            names.append(name)

    def test_clean_releases_simple(self):
        result = ansible.run("clean_releases", {"path": str(self.releases)})
        self.assertTrue(result.get("changed"), result)
        self.assertEqual(listdir(self.releases), {"r2", "r3"})

    def test_check_mode(self):
        result = ansible.run("clean_releases", {
            "path": str(self.releases),
            "_ansible_check_mode": True,
        })
        self.assertTrue(result.get("changed"), result)
        self.assertEqual(listdir(self.releases), {"r0", "r1", "r2", "r3"})

    def test_clean_releases_with_current(self):
        (self.releases / "current").symlink_to(self.release_names[2], True)
        result = ansible.run("clean_releases", {"path": str(self.releases)})
        self.assertTrue(result.get("changed"), result)
        self.assertEqual(listdir(self.releases), {"r2", "r3", "current"})

    def test_clean_releases_with_old_current(self):
        (self.releases / "current").symlink_to(self.release_names[1], True)
        result = ansible.run("clean_releases", {"path": str(self.releases)})
        self.assertTrue(result.get("changed"), result)
        self.assertEqual(listdir(self.releases), {"r1", "r3", "current"})

    def test_clean_releases_with_oldest_current(self):
        (self.releases / "current").symlink_to(self.release_names[0], True)
        result = ansible.run("clean_releases", {"path": str(self.releases)})
        self.assertTrue(result.get("changed"), result)
        self.assertEqual(listdir(self.releases), {"r0", "r3", "current"})

    def test_clean_releases_with_keep_until(self):
        one_minute_from_now = datetime.utcnow() + timedelta(minutes=1)
        self.keep_release(self.release_names[0], one_minute_from_now)
        result = ansible.run("clean_releases", {"path": str(self.releases)})
        self.assertTrue(result.get("changed"), result)
        self.assertEqual(listdir(self.releases), {"r0", "r2", "r3"})

    def test_clean_releases_with_expired_keep_until(self):
        one_minute_ago = datetime.utcnow() - timedelta(minutes=1)
        self.keep_release(self.release_names[0], one_minute_ago)
        result = ansible.run("clean_releases", {"path": str(self.releases)})
        self.assertTrue(result.get("changed"), result)
        self.assertEqual(listdir(self.releases), {"r2", "r3"})

    def test_clean_releases_with_file(self):
        (self.releases / "not-a-dir").touch()
        result = ansible.run("clean_releases", {"path": str(self.releases)})
        self.assertTrue(result.get("changed"), result)
        self.assertEqual(listdir(self.releases), {"r2", "r3", "not-a-dir"})

    def test_clean_releases_with_exclude(self):
        result = ansible.run("clean_releases", {
            "path": str(self.releases),
            "exclude": ["r3"],
        })
        self.assertTrue(result.get("changed"), result)
        self.assertEqual(listdir(self.releases), {"r1", "r2", "r3"})

    def test_clean_releases_with_exclude_current(self):
        (self.releases / "current").symlink_to(self.release_names[2], True)
        result = ansible.run("clean_releases", {
            "path": str(self.releases),
            "exclude": ["r2"],
        })
        self.assertTrue(result.get("changed"), result)
        self.assertEqual(listdir(self.releases), {"r1", "r2", "r3", "current"})

    def test_clean_releases_with_keep(self):
        result = ansible.run("clean_releases", {
            "path": str(self.releases),
            "keep": 3,
        })
        self.assertTrue(result.get("changed"), result)
        self.assertEqual(listdir(self.releases), {"r1", "r2", "r3"})

    def test_clean_releases_with_failed_release(self):
        (self.releases / "r3.failed").mkdir()
        result = ansible.run("clean_releases", {"path": str(self.releases)})
        self.assertTrue(result.get("changed"), result)
        self.assertEqual(listdir(self.releases), {"r2", "r3"})

    def test_clean_releases_with_shared_dir(self):
        shared_dir = Path(test_context(self, tempdir()))
        shares = {}
        for i in range(4):
            name = f"r{i}"
            shares[name] = self.add_shared(name, shared_dir)
        self.assertEqual(listdir(shared_dir), set(shares.values()))
        (shared_dir / "other").touch()
        result = ansible.run("clean_releases", {
            "path": str(self.releases),
            "shared_dir_for_staticfiles": str(shared_dir)
        })
        self.assertTrue(result.get("changed"), result)
        self.assertEqual(listdir(self.releases), {"r2", "r3"})
        self.assertEqual(listdir(shared_dir), {shares["r2"], shares["r3"], "other"})

    def test_clean_releases_with_shared_dir_and_missing_code_version(self):
        shared_dir = Path(test_context(self, tempdir()))
        shares = {}
        for i in range(4):
            name = f"r{i}"
            shares[name] = self.add_shared(name, shared_dir)
            if i < 3:
                os.remove(self.releases / name / ".staticfiles-version")
        (shared_dir / "other").touch()
        result = ansible.run("clean_releases", {
            "path": str(self.releases),
            "shared_dir_for_staticfiles": str(shared_dir)
        })
        self.assertTrue(result.get("changed"), result)
        self.assertEqual(listdir(self.releases), {"r2", "r3"})
        self.assertEqual(listdir(shared_dir), set(shares.values()) | {"other"})

    def test_clean_releases_with_shared_dir_and_multi_referenced_code_version(self):
        shared_dir = Path(test_context(self, tempdir()))
        shares = {}
        SHARED_VERSION = "abc123"
        for i in range(4):
            name = f"r{i}"
            code_version = SHARED_VERSION if i in [1, 2] else None
            shares[name] = self.add_shared(name, shared_dir, code_version)
        assert shares["r1"] == SHARED_VERSION, shares  # validate setup
        assert shares["r2"] == SHARED_VERSION, shares  # validate setup
        self.assertEqual(listdir(shared_dir), set(shares.values()))
        (shared_dir / "other").touch()
        result = ansible.run("clean_releases", {
            "path": str(self.releases),
            "shared_dir_for_staticfiles": str(shared_dir)
        })
        self.assertTrue(result.get("changed"), result)
        self.assertEqual(listdir(self.releases), {"r2", "r3"})
        self.assertEqual(listdir(shared_dir), {SHARED_VERSION, shares["r3"], "other"})

    def test_clean_releases_does_not_delete_hidden_directories(self):
        hidden_dir = self.releases / ".git_mirrors"
        hidden_dir.mkdir()
        result = ansible.run("clean_releases", {"path": str(self.releases)})
        self.assertTrue(result.get("changed"), result)
        self.assertNotIn(".git_mirrors", result["diff"]["before"]["releases"])
        self.assertNotIn(".git_mirrors", result["diff"]["after"]["releases"])
        self.assertEqual(listdir(self.releases), {"r2", "r3", ".git_mirrors"})
        self.assertTrue(hidden_dir.is_dir())

    def make_release(self, name, keep_until=None):
        (self.releases / name).mkdir()
        (self.releases / name / ".build-complete").touch()
        if keep_until is not None:
            self.keep_release(name, keep_until)

    def add_shared(self, release_name, shared_dir, code_version=None):
        if not code_version:
            code_version = sha1(release_name.encode("utf-8")).hexdigest()
        with open(self.releases / release_name / ".staticfiles-version", "w") as fh:
            fh.write(code_version)
        (shared_dir / code_version / "staticfiles/CACHE").mkdir(parents=True, exist_ok=True)
        (shared_dir / code_version / "staticfiles/CACHE/manifest.json").touch()
        return code_version

    def keep_release(self, name, until):
        (self.releases / name / f"KEEP_UNTIL__{until:%Y-%m-%d_%H.%M}").touch()


def listdir(path):
    return {p.name for p in path.iterdir()}
