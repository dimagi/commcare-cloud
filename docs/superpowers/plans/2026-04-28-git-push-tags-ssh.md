# Push deploy tags via SSH — Implementation Plan

> **For agentic workers:** REQUIRED SUB-SKILL: Use superpowers:subagent-driven-development (recommended) or superpowers:executing-plans to implement this plan task-by-task. Steps use checkbox (`- [ ]`) syntax for tracking.

**Goal:** Replace the GitHub-API-based deploy tag creation with a native `git push` over SSH that uses the forwarded SSH agent on the control machine, and remove the now-unneeded write-scope PAT prompt.

**Architecture:** `create_release_tag` in `src/commcare_cloud/commands/deploy/utils.py` keeps its signature and call sites, but its body is rewritten. It builds an SSH URL from `repo.full_name` and tag name from `environment`, then calls a new private helper `_push_release_tag(remote_url, sha, tag_name)` that runs `git init --bare`, `git fetch --depth=1`, `git push <sha>:refs/tags/<name>` in a temp directory. Failures are caught and logged; deploy still records as successful — same contract as today. `src/commcare_cloud/github.py` loses `require_write_permissions`, `repo_is_private`, and the entire interactive `get_github_credentials` prompt path; only opportunistic, non-prompting token lookup remains.

**Tech Stack:** Python 3.10, `subprocess.run`, `tempfile.mkdtemp`, `unittest.TestCase` driven by `nosetests` (per `.tests/tests.sh`), PyGithub (kept for read-only API).

**Spec:** `docs/superpowers/specs/2026-04-28-git-push-tags-ssh-design.md`

---

## File Map

- **Modify** `src/commcare_cloud/commands/deploy/utils.py` — rewrite `create_release_tag`, add `_push_release_tag`, replace `GithubException` import with `subprocess.CalledProcessError` handling.
- **Modify** `src/commcare_cloud/github.py` — drop `require_write_permissions` and `repo_is_private` parameters, drop write-perm check, remove `get_github_credentials`.
- **Modify** `src/commcare_cloud/commands/deploy/commcare.py:144-145` — stop computing `tag_commits` for `github_repo()` and stop passing `require_write_permissions`.
- **Modify** `src/commcare_cloud/commands/deploy/formplayer.py:56-57` — same pattern.
- **Create** `tests/test_deploy/test_create_release_tag.py` — integration tests against a local bare repo via `file://` URL.

---

## Task 1: Failing test for happy-path tag push

**Files:**
- Create: `tests/test_deploy/test_create_release_tag.py`
- Test: `tests/test_deploy/test_create_release_tag.py::TestPushReleaseTag::test_push_creates_tag_at_sha`

- [ ] **Step 1: Write the failing test**

Create `tests/test_deploy/test_create_release_tag.py`:

```python
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
```

- [ ] **Step 2: Run test to verify it fails**

Run: `nosetests -v tests/test_deploy/test_create_release_tag.py:TestPushReleaseTag.test_push_creates_tag_at_sha`

Expected: FAIL with `ImportError: cannot import name '_push_release_tag'`.

- [ ] **Step 3: Commit**

```bash
git add tests/test_deploy/test_create_release_tag.py
git commit -m "test: add failing test for SSH-based release tag push"
```

---

## Task 2: Implement `_push_release_tag` and rewrite `create_release_tag`

**Files:**
- Modify: `src/commcare_cloud/commands/deploy/utils.py:1-48`
- Test: `tests/test_deploy/test_create_release_tag.py::TestPushReleaseTag::test_push_creates_tag_at_sha`

- [ ] **Step 1: Replace the import and rewrite both functions**

Edit `src/commcare_cloud/commands/deploy/utils.py`. Replace:

```python
from datetime import datetime

import attr
from github.GithubException import GithubException
import pytz
from memoized import memoized
```

with:

```python
import shutil
import subprocess
import tempfile
from datetime import datetime

import attr
import pytz
from memoized import memoized
```

Then replace the existing `create_release_tag` (lines 38-48) with:

```python
def create_release_tag(environment, repo, diff):
    if not environment.fab_settings_config.tag_deploy_commits:
        return
    remote_url = f"git@github.com:{repo.full_name}.git"
    tag_name = f"{environment.release_name}-{environment.name}-deploy"
    try:
        _push_release_tag(remote_url, diff.deploy_commit, tag_name)
    except (subprocess.CalledProcessError, OSError) as e:
        print(color_error(f"Error creating release tag: {e}"))


def _push_release_tag(remote_url, sha, tag_name):
    tmp = tempfile.mkdtemp(prefix="cchq-tag-")
    try:
        subprocess.run(
            ["git", "-C", tmp, "init", "--bare", "-q"],
            check=True,
        )
        subprocess.run(
            ["git", "-C", tmp, "fetch", "--depth=1", "--no-tags", remote_url, sha],
            check=True,
        )
        subprocess.run(
            ["git", "-C", tmp, "push", remote_url, f"{sha}:refs/tags/{tag_name}"],
            check=True,
        )
    finally:
        shutil.rmtree(tmp, ignore_errors=True)
```

- [ ] **Step 2: Run the happy-path test to verify it passes**

Run: `nosetests -v tests/test_deploy/test_create_release_tag.py:TestPushReleaseTag.test_push_creates_tag_at_sha`

Expected: PASS.

- [ ] **Step 3: Run full deploy test module to confirm no regressions**

Run: `nosetests -v tests/test_deploy/`

Expected: all tests pass (the tag-related code in other tests isn't exercised yet — they'll be untouched).

- [ ] **Step 4: Commit**

```bash
git add src/commcare_cloud/commands/deploy/utils.py
git commit -m "feat: push deploy tags via SSH instead of GitHub API"
```

---

## Task 3: Failing test for push-failure path

**Files:**
- Modify: `tests/test_deploy/test_create_release_tag.py`
- Test: `tests/test_deploy/test_create_release_tag.py::TestCreateReleaseTag::test_push_failure_is_swallowed`

- [ ] **Step 1: Consolidate imports, add helpers, add new test class**

Edit `tests/test_deploy/test_create_release_tag.py`. Add three imports to the top block (`StringIO`, `MagicMock`/`patch`) and extend the existing `_push_release_tag` import to also bring in `create_release_tag`. Add three module-level factory helpers above `class TestPushReleaseTag` (they are reused by Task 4). Add `class TestCreateReleaseTag` after `TestPushReleaseTag`.

The full file should become:

```python
import shutil
import subprocess
from io import StringIO
from pathlib import Path
from unittest import TestCase
from unittest.mock import MagicMock, patch

from testil import tempdir

from commcare_cloud.commands.deploy.utils import (
    _push_release_tag,
    create_release_tag,
)


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


class TestCreateReleaseTag(TestCase):

    def test_push_failure_is_swallowed(self):
        with patch("commcare_cloud.commands.deploy.utils._push_release_tag",
                   side_effect=subprocess.CalledProcessError(1, ["git"])), \
             patch("sys.stdout", new_callable=StringIO) as out:
            create_release_tag(
                _fake_environment(tag_deploy_commits=True),
                _fake_repo(),
                _fake_diff(),
            )
        self.assertIn("Error creating release tag", out.getvalue())
```

- [ ] **Step 2: Run the test**

Run: `nosetests -v tests/test_deploy/test_create_release_tag.py:TestCreateReleaseTag.test_push_failure_is_swallowed`

Expected: PASS — the implementation in Task 2 already catches `CalledProcessError` and prints via `color_error`. (This test guards against future regressions; it should pass on first run.)

- [ ] **Step 3: Commit**

```bash
git add tests/test_deploy/test_create_release_tag.py
git commit -m "test: assert release-tag push failures are swallowed"
```

---

## Task 4: Test for `tag_deploy_commits=False` early-return guard

**Files:**
- Modify: `tests/test_deploy/test_create_release_tag.py`
- Test: `tests/test_deploy/test_create_release_tag.py::TestCreateReleaseTag::test_disabled_flag_skips_push`

- [ ] **Step 1: Add the test**

Append to `TestCreateReleaseTag` in `tests/test_deploy/test_create_release_tag.py`:

```python
    def test_disabled_flag_skips_push(self):
        with patch("commcare_cloud.commands.deploy.utils._push_release_tag") as push:
            create_release_tag(
                _fake_environment(tag_deploy_commits=False),
                _fake_repo(),
                _fake_diff(),
            )
        push.assert_not_called()
```

- [ ] **Step 2: Run the test**

Run: `nosetests -v tests/test_deploy/test_create_release_tag.py:TestCreateReleaseTag.test_disabled_flag_skips_push`

Expected: PASS — the early-return guard is preserved from Task 2.

- [ ] **Step 3: Commit**

```bash
git add tests/test_deploy/test_create_release_tag.py
git commit -m "test: assert tag_deploy_commits=False skips git operations"
```

---

## Task 5: Simplify `github.py`

**Files:**
- Modify: `src/commcare_cloud/github.py`

- [ ] **Step 1: Rewrite the file**

Replace the entire contents of `src/commcare_cloud/github.py` with:

```python
import os
from pathlib import Path

from github import Github

from commcare_cloud.commands.command_base import CommandError

PROJECT_ROOT = Path(__file__).parent
GITHUB_TOKEN = None


class GithubException(CommandError):
    pass


def github_repo(repo_name):
    # Optional token is used to get a higher rate limit from GitHub.
    token, _ = get_github_credentials_no_prompt()
    return Github(login_or_token=token).get_repo(repo_name)


def get_github_credentials_no_prompt():
    """
    :return: tuple(token, found_in_legacy_location)
    """
    global GITHUB_TOKEN

    if GITHUB_TOKEN is None:
        GITHUB_TOKEN = os.environ.get("GITHUB_TOKEN")

    if GITHUB_TOKEN is not None:
        return GITHUB_TOKEN, False

    try:
        from .config import GITHUB_APIKEY
        return GITHUB_APIKEY, False
    except ImportError:
        try:
            from .fab.config import GITHUB_APIKEY
            return GITHUB_APIKEY, True
        except ImportError:
            pass

    return None, False
```

What's gone:
- `getpass` import and the entire interactive `get_github_credentials` function.
- `color_warning`, `color_notice` imports (only used by the deleted prompt).
- The `repo_is_private` and `require_write_permissions` parameters on `github_repo()`.
- The post-construction `repo.permissions.push` check.

- [ ] **Step 2: Verify no callers reference removed names**

Run: `grep -rn "get_github_credentials\|require_write_permissions\|repo_is_private" src/ tests/`

Expected: only the in-file definitions in `src/commcare_cloud/github.py` (i.e., `get_github_credentials_no_prompt`); zero hits in `tests/` and zero hits elsewhere in `src/`.

If any hit appears outside `github.py`, fix the caller before proceeding.

- [ ] **Step 3: Commit**

```bash
git add src/commcare_cloud/github.py
git commit -m "refactor: drop interactive PAT prompt and write-perm check"
```

---

## Task 6: Update deploy callers to drop `tag_commits` write-perm plumbing

**Files:**
- Modify: `src/commcare_cloud/commands/deploy/commcare.py:144-145`
- Modify: `src/commcare_cloud/commands/deploy/formplayer.py:55-58`

- [ ] **Step 1: Update `commcare.py`**

In `src/commcare_cloud/commands/deploy/commcare.py`, replace lines 144-145:

```python
    tag_commits = environment.fab_settings_config.tag_deploy_commits
    repo = github_repo('dimagi/commcare-hq', require_write_permissions=tag_commits)
```

with:

```python
    repo = github_repo('dimagi/commcare-hq')
```

- [ ] **Step 2: Update `formplayer.py`**

In `src/commcare_cloud/commands/deploy/formplayer.py`, replace lines 55-58 (function `get_formplayer_deploy_diff`):

```python
def get_formplayer_deploy_diff(environment):
    tag_commits = environment.fab_settings_config.tag_deploy_commits
    repo = github_repo('dimagi/formplayer', require_write_permissions=tag_commits)
    return get_deploy_diff(environment, repo)
```

with:

```python
def get_formplayer_deploy_diff(environment):
    repo = github_repo('dimagi/formplayer')
    return get_deploy_diff(environment, repo)
```

- [ ] **Step 3: Run deploy test suite**

Run: `nosetests -v tests/test_deploy/`

Expected: all tests pass.

- [ ] **Step 4: Commit**

```bash
git add src/commcare_cloud/commands/deploy/commcare.py src/commcare_cloud/commands/deploy/formplayer.py
git commit -m "refactor: stop requiring write-scope PAT in deploy diff"
```

---

## Task 7: Final integration check and existing-tasks cleanup

- [ ] **Step 1: Run the full deploy test module one more time**

Run: `nosetests -v tests/test_deploy/`

Expected: all tests pass.

- [ ] **Step 2: Sanity-check the command imports**

Run: `python -c "from commcare_cloud.commands.deploy.commcare import deploy_commcare; from commcare_cloud.commands.deploy.formplayer import deploy_formplayer; from commcare_cloud.commands.deploy.utils import create_release_tag; print('ok')"`

Expected: `ok`. Catches any leftover `GithubException`/`getpass` reference.

- [ ] **Step 3: Push the branch and open a PR**

```bash
git push -u origin dmr/git-push-tags-ssh
gh pr create --title "Push deploy tags via SSH instead of GitHub API" --body "$(cat <<'EOF'
## Summary
- Replaces the GitHub-API `create_git_ref` call in `create_release_tag` with a native `git push` over SSH that uses the forwarded SSH agent on the control machine
- Drops the interactive PAT prompt and write-scope permission check from `github.py`
- Updates deploy callers to no longer pass `require_write_permissions`

## Test plan
- [ ] `nosetests -v tests/test_deploy/test_create_release_tag.py` passes locally
- [ ] `nosetests -v tests/test_deploy/` passes locally
- [ ] One real deploy with `tag_deploy_commits: yes` to confirm a tag lands on GitHub without a PAT prompt

🤖 Generated with [Claude Code](https://claude.com/claude-code)
EOF
)"
```

Expected: PR URL printed.

---

## Self-Review

**Spec coverage:**
- Tag push mechanism (ephemeral bare clone): Tasks 1–2.
- Tag name and SSH URL derivation: Task 2 step 1.
- Function shape (`_push_release_tag` private helper, public signature unchanged): Task 2 step 1.
- Failure handling (`CalledProcessError`/`OSError` swallowed, warning printed): Tasks 2 and 3.
- `github.py` simplification: Task 5.
- Caller updates (`commcare.py`, `formplayer.py`): Task 6.
- Tests (happy path, failure, disabled flag): Tasks 1, 3, 4.

**Placeholder scan:** No TBDs, no "TODO", no "implement later". Each code step shows the actual code. Each test step shows the actual test body.

**Type/name consistency:**
- `_push_release_tag(remote_url, sha, tag_name)` — same signature in Task 1 (test), Task 2 (impl), Task 3 (mocked), Task 4 (mocked).
- `create_release_tag(environment, repo, diff)` — unchanged signature; matches existing call sites in `commcare.py:214` and `formplayer.py:110`.
- Tag name format `{release_name}-{env_name}-deploy` matches existing string in `utils.py:42-45`.
- `repo.full_name` is the documented PyGithub property — same form already used elsewhere in deploy code.
