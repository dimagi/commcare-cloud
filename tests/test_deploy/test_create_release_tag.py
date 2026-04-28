import shutil
import subprocess
from pathlib import Path
from unittest import TestCase

from testil import tempdir

from commcare_cloud.commands.deploy.utils import _push_release_tag


def _git(cwd, *args, capture=False):
    kw = {"check": True, "cwd": str(cwd)}
    if capture:
        kw["capture_output"] = True
        kw["text"] = True
    return subprocess.run(["git", *args], **kw)


def _init_bare_with_commit(repo_dir):
    """Build a bare repo with one commit; return (file_url, sha)."""
    work = repo_dir.parent / "work"
    work.mkdir()
    _git(work, "init", "-q")
    _git(work, "config", "user.email", "test@example.com")
    _git(work, "config", "user.name", "Test")
    (work / "README").write_text("hello\n")
    _git(work, "add", "README")
    _git(work, "commit", "-q", "-m", "init")
    sha = _git(work, "rev-parse", "HEAD", capture=True).stdout.strip()
    _git(repo_dir.parent, "clone", "--bare", "-q", str(work), str(repo_dir))
    shutil.rmtree(work)
    return f"file://{repo_dir}", sha


class TestPushReleaseTag(TestCase):

    def test_push_creates_tag_at_sha(self):
        with tempdir() as tmp:
            tmp = Path(tmp)
            bare = tmp / "remote.git"
            url, sha = _init_bare_with_commit(bare)

            _push_release_tag(url, sha, "release-2026-04-28-deploy")

            ref = subprocess.run(
                ["git", "--git-dir", str(bare),
                 "rev-parse", "refs/tags/release-2026-04-28-deploy"],
                capture_output=True, text=True, check=True,
            ).stdout.strip()
            self.assertEqual(ref, sha)


from io import StringIO
from unittest.mock import MagicMock, patch

from commcare_cloud.commands.deploy.utils import create_release_tag


def _fake_environment(tag_deploy_commits, release_name="r1", env_name="testenv"):
    env = MagicMock()
    env.fab_settings_config.tag_deploy_commits = tag_deploy_commits
    env.release_name = release_name
    env.name = env_name
    return env


def _fake_repo(full_name="dimagi/commcare-hq"):
    repo = MagicMock()
    repo.full_name = full_name
    return repo


def _fake_diff(sha="abc1234"):
    diff = MagicMock()
    diff.deploy_commit = sha
    return diff


class TestCreateReleaseTag(TestCase):

    def test_push_failure_is_swallowed(self):
        # Point at a non-existent file:// URL so git fetch fails.
        with tempdir() as tmp:
            bad_url = f"file://{tmp}/does-not-exist.git"
            with patch("commcare_cloud.commands.deploy.utils._push_release_tag",
                       side_effect=subprocess.CalledProcessError(128, ["git"])), \
                 patch("sys.stdout", new_callable=StringIO) as out:
                create_release_tag(
                    _fake_environment(tag_deploy_commits=True),
                    _fake_repo(),
                    _fake_diff(),
                )
            self.assertIn("Error creating release tag", out.getvalue())
