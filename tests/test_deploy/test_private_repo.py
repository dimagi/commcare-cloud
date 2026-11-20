import subprocess
from tempfile import TemporaryDirectory
from pathlib import Path

import pytest
from unmagic import fixture

from commcare_cloud.commands.deploy.private_repo import (
    CommitCache,
    PrivateRepoError,
    PrivateRevision,
    resolve_private_revision,
)


@fixture
def git_repos():
    with TemporaryDirectory() as tmp:
        yield Repos(Path(tmp))


class Repos:
    """A public repo, a private repo whose branch adds a commit on top
    of public master, and a cache pointed at the public repo"""

    def __init__(self, tmp):
        self.tmp = tmp
        self.work = tmp / "work"
        self.public = tmp / "public.git"
        self.private = tmp / "private.git"
        git(tmp, "init", "-q", "-b", "master", str(self.work))
        for repo in [self.public, self.private]:
            git(tmp, "init", "-q", "--bare", str(repo))
            git(repo, "config", "uploadpack.allowFilter", "true")
            git(repo, "config", "uploadpack.allowAnySHA1InWant", "true")
        self.a = self.commit("a")
        self.b = self.commit("b")
        git(self.work, "push", "-q", str(self.public), "master")
        git(self.work, "checkout", "-q", "-b", "fix")
        self.p = self.commit("private fix")
        git(self.work, "push", "-q", str(self.private), "fix", "master")
        git(self.work, "checkout", "-q", "master")
        self.cache = CommitCache(tmp / "cache.git", public_url=self.public.as_uri())

    def commit(self, message):
        git(self.work, "commit", "-q", "--allow-empty", "-m", message)
        return git(self.work, "rev-parse", "HEAD")

    def advance_public_master(self):
        c = self.commit("c")
        git(self.work, "push", "-q", str(self.public), "master")
        return c

    def resolve(self, rev):
        return resolve_private_revision(self.private.as_uri(), rev, "master", self.cache)


def git(cwd, *args):
    result = subprocess.run(
        ["git", "-c", "user.name=Test", "-c", "user.email=test@example.com", *args],
        cwd=cwd, capture_output=True, text=True, check=True,
    )
    return result.stdout.strip()


def test_resolve_private_branch():
    repos = git_repos()
    assert repos.resolve("fix") == PrivateRevision(repos.p, repos.b, 1)


def test_resolve_after_public_master_moves_on():
    repos = git_repos()
    repos.advance_public_master()
    assert repos.resolve("fix") == PrivateRevision(repos.p, repos.b, 1)


def test_resolve_private_commit_by_sha():
    repos = git_repos()
    assert repos.resolve(repos.p) == PrivateRevision(repos.p, repos.b, 1)


def test_unknown_rev_raises():
    repos = git_repos()
    with pytest.raises(PrivateRepoError, match="Could not fetch 'nope'"):
        repos.resolve("nope")


def test_cache_is_reused():
    repos = git_repos()
    repos.resolve("fix")
    c = repos.advance_public_master()
    assert repos.cache.fetch_public("master") == c
    assert repos.resolve("fix") == PrivateRevision(repos.p, repos.b, 1)
