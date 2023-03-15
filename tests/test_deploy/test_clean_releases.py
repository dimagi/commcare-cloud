from datetime import datetime, timedelta
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

    def make_release(self, name, keep_until=None):
        (self.releases / name).mkdir()
        (self.releases / name / ".build-complete").touch()
        if keep_until is not None:
            self.keep_release(name, keep_until)

    def keep_release(self, name, until):
        (self.releases / name / f"KEEP_UNTIL__{until:%Y-%m-%d_%H.%M}").touch()


def listdir(path):
    return {p.name for p in path.iterdir()}
