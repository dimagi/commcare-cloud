"""Resolve revisions of the private code repo against public commcare-hq history.

Uses a local, commit-only (no trees or blobs) git cache of commcare-hq history,
so no GitHub API access to the private repo is needed. The private repo is
fetched over SSH with the deployer's own GitHub key.
"""
import os
import subprocess
from collections import namedtuple
from pathlib import Path

from commcare_cloud.github import GITHUB_KNOWN_HOSTS

PUBLIC_REPO_URL = "https://github.com/dimagi/commcare-hq.git"
DEFAULT_CACHE_PATH = Path.home() / ".cache" / "commcare-cloud" / "commcare-hq-commits.git"

PrivateRevision = namedtuple("PrivateRevision", "sha public_base private_commit_count")


class PrivateRepoError(Exception):
    pass


def resolve_private_revision(private_url, rev, public_branch, cache=None):
    """Resolve `rev` and find the newest public commit it contains

    :param private_url: SSH URL of the private repo.
    :param rev: Branch, tag, or full commit SHA.
    :param public_branch: Public commcare-hq branch the deploy is based on
        (the environment's default branch).
    :returns: `PrivateRevision`. `private_commit_count` is the number of
        commits in `rev` that are not in the public branch.
    """
    cache = cache or CommitCache()
    public_head = cache.fetch_public(public_branch)
    sha = cache.fetch_private(private_url, rev)
    base = cache.merge_base(sha, public_head)
    if base is None:
        raise PrivateRepoError(f"{rev} shares no history with public {public_branch}")
    return PrivateRevision(sha, base, cache.count_only_in(sha, public_head))


class CommitCache:
    def __init__(self, path=DEFAULT_CACHE_PATH, public_url=PUBLIC_REPO_URL):
        self.path = Path(path)
        self.public_url = public_url

    def fetch_public(self, branch):
        ref = f"refs/public/{branch}"
        self._fetch(self.public_url, f"+refs/heads/{branch}:{ref}")
        return self._git("rev-parse", ref)

    def fetch_private(self, url, rev):
        try:
            self._fetch(url, rev, ssh=True)
        except PrivateRepoError as e:
            raise PrivateRepoError(
                f"Could not fetch {rev!r} from {url}. Use a branch, tag, or full "
                f"commit SHA, and check that your GitHub SSH key can read the repo.\n{e}"
            )
        sha = self._git("rev-parse", "FETCH_HEAD^{commit}")
        # Keep fetched private commits referenced so later fetches can
        # negotiate against them, and so they survive gc.
        self._git("update-ref", f"refs/private/{sha}", sha)
        return sha

    def merge_base(self, a, b):
        result = self._run("merge-base", a, b, check=False)
        return result.stdout.strip() if result.returncode == 0 else None

    def count_only_in(self, commit, other):
        return int(self._git("rev-list", "--count", commit, f"^{other}"))

    def _fetch(self, url, refspec, ssh=False):
        if not (self.path / "HEAD").exists():
            self.path.mkdir(parents=True, exist_ok=True)
            self._git("init", "--quiet", "--bare")
        env = None
        if ssh:
            env = {"GIT_SSH_COMMAND": (
                f"ssh -o UserKnownHostsFile={GITHUB_KNOWN_HOSTS} "
                "-o StrictHostKeyChecking=yes"
            )}
        # The cache must hold refs to previously fetched history (refs/public/*)
        # so the server sends only new commits; without them, fetching from the
        # private repo would transfer its entire history.
        self._git("fetch", "--quiet", "--no-tags", "--filter=tree:0", url, refspec, env=env)

    def _git(self, *args, env=None):
        return self._run(*args, env=env).stdout.strip()

    def _run(self, *args, env=None, check=True):
        full_env = {**os.environ, **env} if env else None
        result = subprocess.run(
            ["git", f"--git-dir={self.path}", *args],
            capture_output=True, text=True, env=full_env,
        )
        if check and result.returncode != 0:
            raise PrivateRepoError(
                f"git {' '.join(args)} failed: {result.stderr.strip()}"
            )
        return result
