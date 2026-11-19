import shutil
import tarfile
from tempfile import TemporaryDirectory as tempdir
from configparser import ConfigParser
from contextlib import contextmanager
from pathlib import Path
from unittest import TestCase
from unittest.mock import patch

import sh

from .. import ansible
from ..utils import set_log_level, test_context


class TestGitSetupRelease(TestCase):

    def test_seed_mirror_from_existing(self):
        refs = self.releases / "refs"
        ansible.run("git_setup_release", {
            "repo": self.src_repo,
            "version": "init",
            "dest": str(self.releases / "one"),
            "reference": str(refs),
        })
        private_repo = self.copy_src_repo("private-hq.git")

        result = ansible.run("git_setup_release", {
            "repo": private_repo,
            "version": "init",
            "dest": str(self.releases / "two"),
            "reference": str(refs),
            "seed_mirror": "mock-hq.git",
        })

        self.assertEqual(result.get("changed"), True, result)
        assert (refs / "private-hq.git").is_dir(), listdir(refs)
        alternates = refs / "private-hq.git/objects/info/alternates"
        self.assertFalse(alternates.exists(), "mirror should be dissociated")
        assert (self.releases / "two/.git").is_dir()

    def test_seed_mirror_missing_falls_back(self):
        release = self.releases / "two"
        refs = self.releases / "refs"
        private_repo = self.copy_src_repo("private-hq.git")

        result = ansible.run("git_setup_release", {
            "repo": private_repo,
            "version": "init",
            "dest": str(release),
            "reference": str(refs),
            "seed_mirror": "nope.git",
        })

        self.assertEqual(result.get("changed"), True, result)
        assert (refs / "private-hq.git").is_dir(), listdir(refs)
        assert (release / ".git").is_dir(), listdir(release)

    def test_seed_mirror_clone_command(self):
        mirrors = self.releases / "refs"
        (mirrors / "seed.git").mkdir(parents=True)
        hq_url = "git@github.com:example/hq.git"
        sub_url = "https://github.com/example/sub.git"

        commands = self.setup_fake_release(hq_url, sub_url, seed_mirror="seed.git")

        self.assertEqual(commands[0], [
            "git", "clone", "--mirror",
            "--reference", mirrors / "seed.git", "--dissociate",
            hq_url, mirrors / "hq.git",
        ])
        sub_clones = [c for c in commands if c[:3] == ["git", "clone", "--mirror"]
                      and sub_url in c]
        self.assertEqual(sub_clones, [
            ["git", "clone", "--mirror", sub_url, mirrors / "sub.git"],
        ])

    def test_missing_seed_mirror_clone_command(self):
        mirrors = self.releases / "refs"
        hq_url = "git@github.com:example/hq.git"
        sub_url = "https://github.com/example/sub.git"

        commands = self.setup_fake_release(hq_url, sub_url, seed_mirror="seed.git")

        self.assertEqual(commands[0], [
            "git", "clone", "--mirror", hq_url, mirrors / "hq.git",
        ])

    def setup_fake_release(self, url, sub_url, seed_mirror):
        """Run Release.setup with a fake run_command; return the commands"""
        module = ansible.import_module("git_setup_release")
        commands = []

        def run_command(args, **kw):
            commands.append(args)
            if args[:2] == ["git", "rev-parse"]:
                return 0, "abc123\n", ""
            return 0, "", ""

        release = module.Release(
            self.releases / "refs", run_command, {"before": {}, "after": {}})
        submodules = [iter([("sub", sub_url, "def456")]), iter([])]
        with patch.object(module.Release, "iter_submodules", side_effect=submodules):
            release.setup(self.releases / "rel", url, "abc123",
                          self.releases / "prev", seed_mirror=seed_mirror)
        return commands

    def test_key_file_only_for_top_level(self):
        module = ansible.import_module("git_setup_release")
        calls = []

        def run_command(args, **kw):
            calls.append((args, kw.get("cwd"), kw.get("environ_update")))
            if args[:2] == ["git", "rev-parse"]:
                return 0, "abc123\n", ""
            if args[:2] == ["git", "cat-file"]:
                return 1, "", ""  # commit missing: force fetch
            return 0, "", ""

        mirrors = self.releases / "refs"
        release_path = self.releases / "rel"
        hq_url = "git@github.com:example/hq.git"
        sub_url = "https://github.com/example/sub.git"
        release = module.Release(
            mirrors, run_command, {"before": {}, "after": {}},
            key_file="/k", known_hosts_file="/kh",
        )
        submodules = [iter([("sub", sub_url, "def456")]), iter([])]
        with patch.object(module.Release, "iter_submodules", side_effect=submodules):
            release.setup(release_path, hq_url, "abc123", self.releases / "prev")

        sub_targets = {sub_url, mirrors / "sub.git", release_path / "sub"}
        remote_commands = {"clone", "remote", "fetch", "checkout"}
        top_calls = []
        other_calls = []
        for args, cwd, env in calls:
            is_sub = cwd in sub_targets or any(a in sub_targets for a in args)
            if not is_sub and args[1] in remote_commands:
                top_calls.append((args, env))
            else:
                other_calls.append((args, env))
        self.assertEqual(
            [args[1] for args, env in top_calls],
            ["clone", "fetch", "clone", "checkout"],
        )
        self.assertTrue(any(args[1] == "clone" for args, env in other_calls))
        for args, env in top_calls:
            self.assertEqual(env, {"GIT_SSH_COMMAND": (
                "ssh -i /k -o IdentitiesOnly=yes"
                " -o UserKnownHostsFile=/kh -o StrictHostKeyChecking=yes"
            )}, args)
        for args, env in other_calls:
            self.assertIsNone(env, args)

    @classmethod
    def setUpClass(cls):
        cls._tmp = tmp = Path(test_context(cls, tempdir()))
        test_context(cls, set_log_level("datadog"))
        cls.repos = tmp / "repos"
        cls.repos.mkdir()
        cls.create_mock_repository()
        cls.src_repo = str(cls.repos / "mock-hq.git")

    def setUp(self):
        self.releases = self._tmp / "releases"
        self.releases.mkdir()
        self.addCleanup(shutil.rmtree, self.releases)

    def test_initial_release(self):
        release = self.releases / "one"
        refs = self.releases / "refs"
        result = ansible.run("git_setup_release", {
            "repo": self.src_repo,
            "version": "init",
            "dest": str(release),
            "reference": str(refs),
        })
        self.assertEqual(result.get("changed"), True, result)
        diff = result["diff"]
        self.assertIn("before", diff, diff)
        self.assertIn("after", diff, diff)

        assert (refs / "mock-hq.git").is_dir(), listdir(refs)
        assert (refs / "load.sh.git").is_dir(), listdir(refs)

        assert release.is_dir(), release
        assert (release / ".git").is_dir(), listdir(release)
        assert_file_content(
            release / "requirements/prod-requirements.txt",
            "testil==1.0",
        )
        self.assertIn("LICENSE", listdir(release / "submodules/load.sh"))

    def test_with_previous_release(self):
        one = self.releases / "one"
        two = self.releases / "two"
        refs = self.releases / "refs"
        version_two = "fb93a93c010da44988735828aac6ace6f852cf4b"
        # first release
        ansible.run("git_setup_release", {
            "repo": self.src_repo,
            "version": "init",
            "dest": str(one),
            "reference": str(refs),
        })
        current = self.releases / "current"
        current.symlink_to(one)
        # second release
        result = ansible.run("git_setup_release", {
            "repo": self.src_repo,
            "version": version_two,
            "dest": str(two),
            "reference": str(refs),
            "previous_release": str(current),
        })

        self.assertEqual(result.get("changed"), True, result)
        diff = result["diff"]
        modules = ConfigParser()
        with open(one / ".gitmodules") as fh:
            modules.read_file(fh)
        print(modules.sections())
        submodule_url = modules['submodule "submodules/load.sh"']['url']
        self.assertEqual(diff["before"], {
            "path": str(one),
            self.src_repo: "52ce898cce4abe7ea89cbe904c658cee65889ead",
            submodule_url: "6d83ae6de4a52c5c3949c3bc5a0d670f6fcc32e2",
        })
        self.assertEqual(diff["after"], {
            "path": str(two),
            self.src_repo: version_two,
            submodule_url: "9136c0e1f2f85a8ebbc9a174e1f92b35e8ca0030",
        })
        assert_file_content(
            two / "requirements/prod-requirements.txt",
            "testil==1.1",
        )
        assert_file_content(
            two / "submodules/load.sh/README.md",
            "Bash Environment Loader",
        )

    def test_new_upstream_commits(self):
        old = self.releases / "old"
        new = self.releases / "new"
        refs = self.releases / "refs"
        version_two = "fb93a93c010da44988735828aac6ace6f852cf4b"
        ansible.run("git_setup_release", {
            "repo": str(self.repos / "mock-hq.git"),
            "version": "init",
            "dest": str(old),
            "reference": str(refs),
        })

        with self.add_commit_to_src_repo() as version:
            result = ansible.run("git_setup_release", {
                "repo": str(self.repos / "mock-hq.git"),
                "version": "master",
                "dest": str(new),
                "reference": str(refs),
                "previous_release": str(old),
            })

        self.assertNotEqual(version, version_two)
        self.assertEqual(result.get("changed"), True, result)
        diff = result["diff"]
        mock_hq_repo = self.src_repo
        self.assertEqual(diff["after"][mock_hq_repo], version, diff)

    def test_no_change_when_release_exists(self):
        release = self.releases / "rel"
        refs = self.releases / "refs"
        ansible.run("git_setup_release", {
            "repo": self.src_repo,
            "version": "init",
            "dest": str(release),
            "reference": str(refs),
        })

        result = ansible.run("git_setup_release", {
            "repo": self.src_repo,
            "version": "init",
            "dest": str(release),
            "reference": str(refs),
        })
        self.assertEqual(result.get("changed"), False, result)
        diff = result["diff"]
        self.assertEqual(diff["before"], diff["after"])

    def test_bad_repo(self):
        release = self.releases / "rel"
        refs = self.releases / "refs"
        with self.assertRaisesRegex(ValueError, "invalid repository URL: /"):
            ansible.run("git_setup_release", {
                "repo": "/",
                "version": "init",
                "dest": str(release),
                "reference": str(refs),
            })
        self.assertFalse(release.exists())
        self.assertFalse(refs.exists())

    def test_incomplete_release(self):
        release = self.releases / "rel"
        refs = self.releases / "refs"
        rel_tmp = release.with_suffix(".tmp")
        rel_tmp.mkdir()  # simulate release in progress
        with self.assertRaisesRegex(ansible.Fail, f"Found incomplete release: {rel_tmp}"):
            ansible.run("git_setup_release", {
                "repo": self.src_repo,
                "version": "init",
                "dest": str(release),
                "reference": str(refs),
            })
        self.assertFalse(listdir(rel_tmp))
        self.assertFalse(release.exists())
        self.assertFalse(refs.exists())

    def test_bad_version(self):
        release = self.releases / "one"
        refs = self.releases / "refs"
        with self.assertRaisesRegex(ansible.Fail, "couldn't find remote ref bad-version"):
            ansible.run("git_setup_release", {
                "repo": self.src_repo,
                "version": "bad-version",
                "dest": str(release),
                "reference": str(refs),
            })
        self.assertFalse(release.with_suffix(".tmp").exists())
        self.assertFalse(release.exists())

    def test_no_version(self):
        release = self.releases / "one"
        refs = self.releases / "refs"
        with self.assertRaisesRegex(ansible.Fail, "Cannot setup release without code version"):
            ansible.run("git_setup_release", {
                "repo": self.src_repo,
                "version": "",
                "dest": str(release),
                "reference": str(refs),
            })
        self.assertFalse(release.with_suffix(".tmp").exists())
        self.assertFalse(release.exists())

    def test_known_hosts_file_requires_key_file(self):
        release = self.releases / "rel"
        with self.assertRaisesRegex(ansible.Fail, "required by 'known_hosts_file': key_file"):
            ansible.run("git_setup_release", {
                "repo": self.src_repo,
                "version": "init",
                "dest": str(release),
                "reference": str(self.releases / "refs"),
                "known_hosts_file": "/kh",
            })
        self.assertFalse(release.exists())

    def test_check_mode(self):
        release = self.releases / "rel"
        refs = self.releases / "refs"
        ansible.run("git_setup_release", {
            "repo": self.src_repo,
            "version": "init",
            "dest": str(release),
            "reference": str(refs),
            "_ansible_check_mode": True,
        })
        self.assertFalse(release.with_suffix(".tmp").exists())
        self.assertFalse(release.exists())
        self.assertFalse(refs.exists())

    @classmethod
    def create_mock_repository(cls):
        """Extract "mock-hq.git" as bare repository from .tbz file"""
        mock_hq_tbz = Path(__file__).parent / "mock-hq.git.tbz"
        with tarfile.open(mock_hq_tbz) as tarball:
            tarball.extractall(cls.repos)

    def copy_src_repo(self, name):
        path = self.repos / name
        shutil.copytree(self.repos / "mock-hq.git", path)
        self.addCleanup(shutil.rmtree, path)
        return str(path)

    @contextmanager
    def add_commit_to_src_repo(self):
        sh.git("clone", self.repos / "mock-hq.git", _cwd=self.repos)
        git = sh.git.bake(_cwd=self.repos / "mock-hq", _env={
            "EMAIL": "test@test.com",
            "GIT_AUTHOR_NAME": "Test",
            "GIT_COMMITTER_NAME": "Test",
        })
        git("commit", "--allow-empty", "-m", "empty commit")
        git("push")
        try:
            yield str(git("rev-parse", "HEAD")).strip()
        finally:
            shutil.rmtree(self.repos)
            self.repos.mkdir()
            self.create_mock_repository()


def listdir(path):
    return {p.name for p in path.iterdir()}


def assert_file_content(path, content):
    with open(path) as fh:
        data = fh.read()
    assert content in data, f"{content!r} not in {path}:\n{data}"
