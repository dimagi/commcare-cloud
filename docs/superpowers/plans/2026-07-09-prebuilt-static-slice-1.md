# Prebuilt Static Files — Slice 1 (Fetch to Control Machine) Implementation Plan

> **For agentic workers:** REQUIRED SUB-SKILL: Use superpowers:subagent-driven-development (recommended) or superpowers:executing-plans to implement this plan task-by-task. Steps use checkbox (`- [ ]`) syntax for tracking.

**Goal:** When `cchq <env> deploy commcare --prebuilt-static` is run, download the prebuilt `REQUIRED_STATIC_FILES.zip` GitHub Actions artifact for the exact deploy commit onto the control machine (unwrapping GitHub's outer zip once), and pass its availability/path to the ansible play — without changing any deploy behavior yet.

**Architecture:** All fetch logic lives in Python inside the deploy command (per the spec: "keep the HTTP/lookup logic in a small testable helper rather than inline ansible"), running *before* `run_ansible_playbook`. The token from `get_github_credentials_no_prompt()` (the same one used for the deploy summary) never reaches ansible; only the non-secret results (`static_artifact_available`, `static_artifact_path`) are passed as `-e` vars for slice 2 to consume. Opt-in is a new `--prebuilt-static` CLI flag on the deploy command — no environment config or schema change. Any failure → warn and fall back silently to the unchanged on-host build.

**Tech Stack:** Python 3, `requests` (already a dependency), `zipfile` (stdlib), `pytest` + `requests_mock` (already used in `tests/test_deploy/test_formplayer_deploy.py`) for tests.

**Spec:** `docs/superpowers/specs/2026-06-25-prebuilt-static-from-github-design.md` (Slice 1 of "Build approach: vertical slices").

## Global Constraints

- The GitHub token must never appear in ansible `-e` args, process listings, or printed output.
- No change to any existing deploy behavior: `staticfiles_collect` / `staticfiles_compress` still run unconditionally; a fetch failure must never fail the deploy. Deploys without `--prebuilt-static` must be byte-for-byte identical to today.
- Artifact name is `staticfiles-<sha>` where `<sha>` is the **full 40-char deploy commit** (`code_version`). Verified against commcare-hq `.github/workflows/build-static.yml`: `name: staticfiles-${{ github.sha }}`. Fetching by `code_version` is what guarantees the static files match the commit being deployed.
- Inner zip layout (verified in commcare-hq `copy_required_static_files.py`): entries are bare top-level static dirs (`hqwebapp/`, `CACHE/`, `jsi18n/`, `webpack/`, ...) — no wrapper directory. Slice 2 unzips it directly into `{{ code_source }}/staticfiles/`.
- Waiting policy: if the artifact isn't available yet, wait **only while the build-static workflow run for the deploy SHA is queued or in progress** (30s interval, 1800s ceiling). No run, or a run that concluded without success → fail fast to the on-host fallback. Never poll blindly.
- GitHub API endpoints: `https://api.github.com/repos/dimagi/commcare-hq/actions/artifacts` (artifact lookup/download) and `https://api.github.com/repos/dimagi/commcare-hq/actions/workflows/build-static.yml/runs?head_sha=<sha>` (run status).
- Run tests from the repo root: `pytest tests/test_deploy/... -v` (venv assumed active).

---

### Task 1: Artifact fetch helper (`static_artifact.py`)

**Files:**
- Create: `src/commcare_cloud/commands/deploy/static_artifact.py`
- Test: `tests/test_deploy/test_static_artifact.py` (create)

**Interfaces:**
- Consumes: nothing from other tasks.
- Produces: `fetch_static_artifact(token: str, sha: str, dest_dir: str, timeout: int = 1800, interval: int = 30, sleep=time.sleep) -> Optional[str]` — returns the absolute path of the inner `REQUIRED_STATIC_FILES.zip` on success, `None` when the artifact isn't available (no build for the SHA, build failed, or build didn't finish within the timeout). Raises `requests.RequestException` / `zipfile.BadZipFile` on hard errors (caller handles). Consumed by Task 2.

- [ ] **Step 1: Write the failing tests**

Create `tests/test_deploy/test_static_artifact.py`:

```python
import io
import zipfile
from pathlib import Path

import requests_mock

from commcare_cloud.commands.deploy.static_artifact import (
    ARTIFACTS_URL,
    RUNS_URL,
    fetch_static_artifact,
)

SHA = "abc123"
LIST_URL = f"{ARTIFACTS_URL}?name=staticfiles-{SHA}"
RUNS_QUERY_URL = f"{RUNS_URL}?head_sha={SHA}"
DOWNLOAD_URL = f"{ARTIFACTS_URL}/999/zip"

NOT_FOUND = {"total_count": 0, "artifacts": []}


def _runs_response(status, conclusion=None):
    return {"workflow_runs": [{"status": status, "conclusion": conclusion}]}


def _zip_bytes(entries):
    """entries: dict of {name: bytes} -> zip file bytes"""
    buf = io.BytesIO()
    with zipfile.ZipFile(buf, "w") as zf:
        for name, data in entries.items():
            zf.writestr(name, data)
    return buf.getvalue()


def _inner_zip():
    # entries are bare top-level static dirs, per copy_required_static_files
    return _zip_bytes({"CACHE/manifest.json": b"{}", "hqwebapp/js/main.js": b""})


def _outer_zip():
    return _zip_bytes({"REQUIRED_STATIC_FILES.zip": _inner_zip()})


def _found_response():
    return {"total_count": 1, "artifacts": [
        {"id": 999, "name": f"staticfiles-{SHA}", "expired": False,
         "archive_download_url": DOWNLOAD_URL},
    ]}


def test_artifact_found_immediately(tmp_path):
    with requests_mock.Mocker() as m:
        m.get(LIST_URL, json=_found_response())
        m.get(DOWNLOAD_URL, content=_outer_zip())
        result = fetch_static_artifact("tok", SHA, str(tmp_path))
    assert result is not None
    assert Path(result).name == "REQUIRED_STATIC_FILES.zip"
    # the inner zip is a valid zip containing the static tree
    assert "CACHE/manifest.json" in zipfile.ZipFile(result).namelist()


def test_waits_while_build_is_running(tmp_path):
    sleeps = []
    with requests_mock.Mocker() as m:
        m.get(LIST_URL, [
            {"json": NOT_FOUND},
            {"json": NOT_FOUND},
            {"json": _found_response()},
        ])
        m.get(RUNS_QUERY_URL, json=_runs_response("in_progress"))
        m.get(DOWNLOAD_URL, content=_outer_zip())
        result = fetch_static_artifact(
            "tok", SHA, str(tmp_path), timeout=1800, interval=30, sleep=sleeps.append)
    assert result is not None
    assert sleeps == [30, 30]


def test_no_workflow_run_fails_fast(tmp_path):
    sleeps = []
    with requests_mock.Mocker() as m:
        m.get(LIST_URL, json=NOT_FOUND)
        m.get(RUNS_QUERY_URL, json={"workflow_runs": []})
        result = fetch_static_artifact(
            "tok", SHA, str(tmp_path), timeout=1800, interval=30, sleep=sleeps.append)
    assert result is None
    assert sleeps == []  # no waiting when there is no build to wait for
    assert m.call_count == 2  # one artifact check + one run check


def test_failed_build_fails_fast(tmp_path):
    sleeps = []
    with requests_mock.Mocker() as m:
        m.get(LIST_URL, json=NOT_FOUND)
        m.get(RUNS_QUERY_URL, json=_runs_response("completed", "failure"))
        result = fetch_static_artifact(
            "tok", SHA, str(tmp_path), timeout=1800, interval=30, sleep=sleeps.append)
    assert result is None
    assert sleeps == []


def test_completed_build_rechecks_artifact_once(tmp_path):
    # Build finished successfully between our artifact check and run check:
    # one final artifact lookup catches it.
    with requests_mock.Mocker() as m:
        m.get(LIST_URL, [{"json": NOT_FOUND}, {"json": _found_response()}])
        m.get(RUNS_QUERY_URL, json=_runs_response("completed", "success"))
        m.get(DOWNLOAD_URL, content=_outer_zip())
        result = fetch_static_artifact(
            "tok", SHA, str(tmp_path), timeout=1800, interval=30, sleep=lambda s: None)
    assert result is not None


def test_build_still_running_at_timeout_returns_none(tmp_path):
    with requests_mock.Mocker() as m:
        m.get(LIST_URL, json=NOT_FOUND)
        m.get(RUNS_QUERY_URL, json=_runs_response("in_progress"))
        result = fetch_static_artifact(
            "tok", SHA, str(tmp_path), timeout=60, interval=30, sleep=lambda s: None)
    assert result is None
    # waited 30, 60 -> ceiling reached after 2 sleeps; 3 artifact checks + 3 run checks
    assert m.call_count == 6


def test_expired_artifact_is_ignored(tmp_path):
    expired = {"total_count": 1, "artifacts": [
        {"id": 5, "name": f"staticfiles-{SHA}", "expired": True,
         "archive_download_url": DOWNLOAD_URL},
    ]}
    with requests_mock.Mocker() as m:
        m.get(LIST_URL, json=expired)
        m.get(RUNS_QUERY_URL, json={"workflow_runs": []})
        result = fetch_static_artifact(
            "tok", SHA, str(tmp_path), timeout=1800, interval=30, sleep=lambda s: None)
    assert result is None


def test_single_wrapped_download_is_used_as_is(tmp_path):
    # If GitHub ever returns the staticfiles zip directly (not zip-of-zip),
    # skip the unwrap and return the download itself.
    with requests_mock.Mocker() as m:
        m.get(LIST_URL, json=_found_response())
        m.get(DOWNLOAD_URL, content=_inner_zip())
        result = fetch_static_artifact("tok", SHA, str(tmp_path))
    assert result is not None
    assert "CACHE/manifest.json" in zipfile.ZipFile(result).namelist()


def test_token_is_sent_as_bearer(tmp_path):
    with requests_mock.Mocker() as m:
        m.get(LIST_URL, json=_found_response())
        m.get(DOWNLOAD_URL, content=_outer_zip())
        fetch_static_artifact("tok", SHA, str(tmp_path))
    for request in m.request_history:
        assert request.headers["Authorization"] == "Bearer tok"
```

- [ ] **Step 2: Run tests to verify they fail**

Run: `pytest tests/test_deploy/test_static_artifact.py -v`
Expected: FAIL with `ModuleNotFoundError: No module named 'commcare_cloud.commands.deploy.static_artifact'`

- [ ] **Step 3: Write the implementation**

Create `src/commcare_cloud/commands/deploy/static_artifact.py`:

```python
"""Fetch the prebuilt REQUIRED_STATIC_FILES.zip GitHub Actions artifact.

The 'Build Static Files' workflow in dimagi/commcare-hq uploads an artifact
named ``staticfiles-<full commit sha>`` for each push to autostaging, so
fetching by the deploy's ``code_version`` guarantees the static files match
the deployed commit. The artifact-download endpoint wraps the zip in an
outer zip; this module unwraps that outer layer once and returns the inner
zip, which slice 2 pushes to the hosts.

See docs/superpowers/specs/2026-06-25-prebuilt-static-from-github-design.md
"""
import os
import time
import zipfile

import requests

ARTIFACTS_URL = "https://api.github.com/repos/dimagi/commcare-hq/actions/artifacts"
RUNS_URL = ("https://api.github.com/repos/dimagi/commcare-hq"
            "/actions/workflows/build-static.yml/runs")
INNER_ZIP_NAME = "REQUIRED_STATIC_FILES.zip"
POLL_TIMEOUT = 1800
POLL_INTERVAL = 30
REQUEST_TIMEOUT = 60
RUNNING_STATUSES = ("queued", "in_progress", "pending", "waiting", "requested")


def fetch_static_artifact(token, sha, dest_dir,
                          timeout=POLL_TIMEOUT, interval=POLL_INTERVAL,
                          sleep=time.sleep):
    """Download the staticfiles artifact for ``sha`` into ``dest_dir``.

    If the artifact isn't available yet, waits while the build-static
    workflow run for ``sha`` is queued or in progress (up to ``timeout``).
    Returns the path to the inner REQUIRED_STATIC_FILES.zip, or None if
    the artifact isn't available (no build for the SHA, build failed, or
    build didn't finish in time). Network and zip errors propagate; the
    caller treats any exception as "artifact unavailable".
    """
    download_url = _wait_for_artifact(token, sha, timeout, interval, sleep)
    if download_url is None:
        return None
    download_path = _download(token, download_url, dest_dir)
    return _unwrap_once(download_path, dest_dir)


def _wait_for_artifact(token, sha, timeout, interval, sleep):
    waited = 0
    while True:
        download_url = _get_artifact_download_url(token, sha)
        if download_url is not None:
            return download_url
        status, conclusion = _get_workflow_run(token, sha)
        if status in RUNNING_STATUSES:
            if waited >= timeout:
                return None
            sleep(interval)
            waited += interval
            continue
        if status == "completed" and conclusion == "success":
            # build finished between the two checks above; the artifact
            # should be listed now — one final lookup
            return _get_artifact_download_url(token, sha)
        # no build for this sha, or it concluded without success
        return None


def _get_workflow_run(token, sha):
    """Return (status, conclusion) of the build-static run for sha.

    (None, None) when the workflow never ran for this commit.
    """
    response = requests.get(
        RUNS_URL,
        params={"head_sha": sha},
        headers=_headers(token),
        timeout=REQUEST_TIMEOUT,
    )
    response.raise_for_status()
    runs = response.json()["workflow_runs"]
    if runs:
        return runs[0]["status"], runs[0]["conclusion"]
    return None, None


def _get_artifact_download_url(token, sha):
    response = requests.get(
        ARTIFACTS_URL,
        params={"name": f"staticfiles-{sha}"},
        headers=_headers(token),
        timeout=REQUEST_TIMEOUT,
    )
    response.raise_for_status()
    artifacts = [a for a in response.json()["artifacts"] if not a["expired"]]
    if artifacts:
        return artifacts[0]["archive_download_url"]
    return None


def _download(token, download_url, dest_dir):
    # GitHub responds 302 to a short-lived blob URL; requests follows it
    # and drops the Authorization header on the cross-host redirect.
    download_path = os.path.join(dest_dir, "artifact-download.zip")
    with requests.get(
        download_url,
        headers=_headers(token),
        timeout=REQUEST_TIMEOUT,
        stream=True,
    ) as response:
        response.raise_for_status()
        with open(download_path, "wb") as f:
            for chunk in response.iter_content(chunk_size=1024 * 1024):
                f.write(chunk)
    return download_path


def _unwrap_once(download_path, dest_dir):
    """Remove GitHub's outer zip wrapper, if present.

    The artifact endpoint returns a zip whose single entry is our
    REQUIRED_STATIC_FILES.zip. If the download is not wrapped that way,
    use it as-is.
    """
    with zipfile.ZipFile(download_path) as outer:
        if outer.namelist() == [INNER_ZIP_NAME]:
            return outer.extract(INNER_ZIP_NAME, dest_dir)
    return download_path


def _headers(token):
    return {
        "Authorization": f"Bearer {token}",
        "Accept": "application/vnd.github+json",
    }
```

- [ ] **Step 4: Run tests to verify they pass**

Run: `pytest tests/test_deploy/test_static_artifact.py -v`
Expected: PASS (9 tests)

Note: `requests_mock` returns content directly with no 302 redirect, so the `test_token_is_sent_as_bearer` assertion over `request_history` validates both real requests carry the header; the redirect-stripping behavior is requests' own and not under test.

- [ ] **Step 5: Commit**

```bash
git add src/commcare_cloud/commands/deploy/static_artifact.py tests/test_deploy/test_static_artifact.py
git commit -m "Add GitHub static artifact fetch helper"
```

---

### Task 2: `--prebuilt-static` CLI flag wired into `deploy_commcare`

**Files:**
- Modify: `src/commcare_cloud/commands/deploy/command.py` (`Deploy.arguments` ~line 28–64; `_warn_about_non_formplayer_args` ~line 120–135)
- Modify: `src/commcare_cloud/commands/deploy/commcare.py` (imports ~line 1–27; `deploy_commcare` ~line 52–70)
- Test: `tests/test_deploy/test_prebuilt_static_args.py` (create)

**Interfaces:**
- Consumes: `fetch_static_artifact(token, sha, dest_dir)` (Task 1); existing `get_github_credentials_no_prompt()` from `commcare_cloud.github`; `args.prebuilt_static: bool` (defined here).
- Produces: extra ansible args `["-e", "static_artifact_available=true", "-e", "static_artifact_path=<path>"]` on success, `[]` otherwise. Slice 2's ansible plays will consume these vars; in slice 1 they are inert (no play references them).

- [ ] **Step 1: Write the failing tests**

Create `tests/test_deploy/test_prebuilt_static_args.py`:

```python
from unittest.mock import Mock, patch

from commcare_cloud.commands.deploy import commcare
from commcare_cloud.commands.deploy.commcare import get_prebuilt_static_args


def _args(prebuilt_static=True):
    return Mock(prebuilt_static=prebuilt_static)


def test_returns_args_when_artifact_fetched():
    with patch.object(commcare, "get_github_credentials_no_prompt", return_value="tok"), \
            patch.object(commcare, "fetch_static_artifact",
                         return_value="/tmp/x/REQUIRED_STATIC_FILES.zip") as fetch:
        args = get_prebuilt_static_args(_args(), "abc123")
    assert args == [
        "-e", "static_artifact_available=true",
        "-e", "static_artifact_path=/tmp/x/REQUIRED_STATIC_FILES.zip",
    ]
    token, sha, dest_dir = fetch.call_args[0]
    assert (token, sha) == ("tok", "abc123")


def test_noop_without_flag():
    with patch.object(commcare, "fetch_static_artifact") as fetch:
        assert get_prebuilt_static_args(_args(prebuilt_static=False), "abc123") == []
    fetch.assert_not_called()


def test_noop_when_no_token():
    with patch.object(commcare, "get_github_credentials_no_prompt", return_value=None), \
            patch.object(commcare, "fetch_static_artifact") as fetch:
        assert get_prebuilt_static_args(_args(), "abc123") == []
    fetch.assert_not_called()


def test_falls_back_when_artifact_not_found():
    with patch.object(commcare, "get_github_credentials_no_prompt", return_value="tok"), \
            patch.object(commcare, "fetch_static_artifact", return_value=None):
        assert get_prebuilt_static_args(_args(), "abc123") == []


def test_falls_back_on_fetch_error():
    with patch.object(commcare, "get_github_credentials_no_prompt", return_value="tok"), \
            patch.object(commcare, "fetch_static_artifact",
                         side_effect=Exception("boom")):
        assert get_prebuilt_static_args(_args(), "abc123") == []
```

- [ ] **Step 2: Run tests to verify they fail**

Run: `pytest tests/test_deploy/test_prebuilt_static_args.py -v`
Expected: FAIL with `ImportError: cannot import name 'get_prebuilt_static_args'`

- [ ] **Step 3: Add the CLI flag**

In `src/commcare_cloud/commands/deploy/command.py`, add to `Deploy.arguments` after `--update-config` (~line 61):

```python
        Argument('--prebuilt-static', action='store_true', help="""
            Fetch the prebuilt static files artifact for the deployed commit
            from GitHub Actions instead of relying solely on the on-host
            build. Requires a GitHub token (GITHUB_TOKEN env var or
            config.py) with Actions read access on dimagi/commcare-hq.
            Falls back to the on-host build if the artifact is unavailable.
        """),
```

And add `'--prebuilt-static',` to the list in `_warn_about_non_formplayer_args` (after `'--update-config',`) so a formplayer-only deploy warns that it's ignored.

- [ ] **Step 4: Implement `get_prebuilt_static_args` and call it from `deploy_commcare`**

In `src/commcare_cloud/commands/deploy/commcare.py`, add imports (near the existing ones at the top):

```python
import tempfile

from commcare_cloud.commands.deploy.static_artifact import fetch_static_artifact
from commcare_cloud.github import get_github_credentials_no_prompt, github_repo
```

(`github_repo` is already imported from `commcare_cloud.github` — extend that line rather than adding a duplicate import.)

Add the function (below `deploy_commcare`):

```python
def get_prebuilt_static_args(args, deploy_commit):
    """Ansible -e args pointing at the prebuilt static artifact, or [].

    Fetches the artifact onto the control machine when --prebuilt-static
    is passed and a GitHub token is available. Any failure falls back to
    the on-host static build (returns []). The token itself is never
    passed to ansible.
    """
    if not args.prebuilt_static:
        return []
    token = get_github_credentials_no_prompt()
    if not token:
        print(color_notice(
            "--prebuilt-static was passed but no GitHub token is "
            "configured (GITHUB_TOKEN env var or config.py). "
            "Falling back to the on-host static build."
        ))
        return []
    print(color_summary(">> Fetching prebuilt static files artifact"))
    dest_dir = tempfile.mkdtemp(prefix="commcare-static-artifact-")
    try:
        zip_path = fetch_static_artifact(token, deploy_commit, dest_dir)
    except Exception as err:
        print(color_error(f"Error fetching prebuilt static artifact: {err}"))
        zip_path = None
    if zip_path is None:
        print(color_notice(
            "Prebuilt static artifact unavailable. "
            "Falling back to the on-host static build."
        ))
        return []
    print(color_summary(f"Prebuilt static artifact downloaded: {zip_path}"))
    return [
        "-e", "static_artifact_available=true",
        "-e", f"static_artifact_path={zip_path}",
    ]
```

In `deploy_commcare`, immediately after `ansible_args.extend(["-e", f"code_version={context.diff.deploy_commit}"])` (line ~53):

```python
    ansible_args.extend(get_prebuilt_static_args(args, context.diff.deploy_commit))
```

- [ ] **Step 5: Run tests to verify they pass**

Run: `pytest tests/test_deploy/test_prebuilt_static_args.py tests/test_deploy/test_command.py -v`
Expected: PASS. `test_command.py` must still pass unchanged — its invocations don't pass `--prebuilt-static`, so `args.prebuilt_static` is `False` and `get_prebuilt_static_args` returns `[]` without touching the network. (If any of its fake `args` objects lack the attribute, that's a real integration break — fix by ensuring the tests build args through the argument parser, not by loosening `get_prebuilt_static_args`.)

- [ ] **Step 6: Check the flag renders in CLI help and autogenerated docs**

Run: `COMMCARE_CLOUD_ENVIRONMENTS=tests/test_envs commcare-cloud staging deploy --help`
Expected: `--prebuilt-static` listed with its help text.

Run: `./tests/test_autogen_docs.sh` (this repo autogenerates command docs from parsers; if it reports a diff, run the regeneration command it names and include the regenerated docs in the commit).

- [ ] **Step 7: Commit**

```bash
git add src/commcare_cloud/commands/deploy/command.py src/commcare_cloud/commands/deploy/commcare.py tests/test_deploy/test_prebuilt_static_args.py
# plus any regenerated docs from step 6
git commit -m "Add --prebuilt-static deploy flag to fetch static artifact"
```

---

### Task 3: End-to-end verification

**Files:** none (verification only).

**Interfaces:**
- Consumes: everything above.
- Produces: slice 1 acceptance evidence.

- [ ] **Step 1: Run the full deploy test suite**

Run: `pytest tests/test_deploy/ -v`
Expected: PASS

- [ ] **Step 2: Manual verification against the real GitHub API (no deploy needed)**


With a GitHub token that has `Actions: Read` on dimagi/commcare-hq, and `<sha>` the full commit SHA of a recent `autostaging` push with a completed "Build Static Files" run (the token is prompted with hidden input — never typed on the command line or stored in shell history):

```bash
python - <<'EOF'
import tempfile, zipfile
from getpass import getpass
from commcare_cloud.commands.deploy.static_artifact import fetch_static_artifact
path = fetch_static_artifact(getpass("GitHub token: "), '<sha>', tempfile.mkdtemp())
print(path)
print(zipfile.ZipFile(path).namelist()[:10])
EOF
```

Expected: prints a path ending in `REQUIRED_STATIC_FILES.zip` and entries rooted at bare static dirs (`CACHE/...`, `hqwebapp/...`, `jsi18n/...`, `webpack/...`) — confirming the layout established from the commcare-hq source holds for the real artifact.

- [ ] **Step 3: Staging deploy with the flag**

Run a staging deploy with `--prebuilt-static`. Expected console output includes `>> Fetching prebuilt static files artifact` and `Prebuilt static artifact downloaded: ...`, and the deploy then proceeds **identically to before** (collect/compress still run on hosts). Also run one deploy *without* the flag and confirm no new output appears.

---

## Out of scope for this plan (slice 2+)

- Pushing the zip to hosts, host-side unzip into `{{ code_source }}/staticfiles/`, manifest/CACHE distribution.
- `when: not static_artifact_available` gating of `staticfiles_collect` / `staticfiles_compress` in `deploy_hq.yml`.
- Cleanup of the control-machine temp dir after distribution.
- Hardening/messaging polish (slice 3).
