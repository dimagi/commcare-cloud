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
    _git(work, "init", "--initial-branch=main", "-q")
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
