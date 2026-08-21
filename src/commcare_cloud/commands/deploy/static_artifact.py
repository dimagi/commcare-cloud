"""Fetch the prebuilt REQUIRED_STATIC_FILES.zip GitHub Actions artifact.

The 'Build Static Files' workflow in dimagi/commcare-hq uploads an artifact
named ``staticfiles-<full commit sha>`` for each push to autostaging, so
fetching by the deploy's ``code_version`` guarantees the static files match
the deployed commit. The artifact-download endpoint wraps the zip in an
outer zip; this module unwraps that outer layer once and returns the inner
zip.

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
PROGRESS_INTERVAL = 10  # seconds between download progress lines
RUNNING_STATUSES = ("queued", "in_progress", "pending", "waiting", "requested")


def fetch_static_artifact(token, sha, dest_dir,
                          timeout=POLL_TIMEOUT, interval=POLL_INTERVAL):
    """Download the staticfiles artifact for ``sha`` into ``dest_dir``.

    If the artifact isn't available yet, waits while the build-static
    workflow run for ``sha`` is queued or in progress (up to ``timeout``).
    Returns the path to the inner REQUIRED_STATIC_FILES.zip, or None if
    the artifact isn't available (no build for the SHA, build failed, or
    build didn't finish in time). Network and zip errors propagate; the
    caller treats any exception as "artifact unavailable".
    """
    download_url = _wait_for_artifact(token, sha, timeout, interval)
    if download_url is None:
        return None
    download_path = _download(token, download_url, dest_dir)
    return _unwrap_once(download_path, dest_dir)


def _wait_for_artifact(token, sha, timeout, interval):
    waited = 0
    while True:
        download_url = _get_artifact_download_url(token, sha)
        if download_url is not None:
            return download_url
        status, conclusion = _get_workflow_run(token, sha)
        if status in RUNNING_STATUSES:
            if waited >= timeout:
                return None
            time.sleep(interval)
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
        total = int(response.headers.get("Content-Length") or 0)
        BYTES_PER_MB = 1024 * 1024
        total_mb = f"/{total / BYTES_PER_MB:.0f}" if total else ""
        received = 0
        last_report = time.monotonic()
        with open(download_path, "wb") as f:
            for chunk in response.iter_content(chunk_size=BYTES_PER_MB):
                f.write(chunk)
                received += len(chunk)
                if time.monotonic() - last_report >= PROGRESS_INTERVAL:
                    print(f"  downloaded {received / BYTES_PER_MB:.0f}{total_mb} MB ...")
                    last_report = time.monotonic()
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


def main(argv=None):
    """CLI entry point, run on the control machine by the deploy playbook.

    Usage: python -m commcare_cloud.commands.deploy.static_artifact <sha> <dest_dir>

    The token is read from the GITHUB_TOKEN environment variable (never
    argv, which is visible in process listings). On success the last line
    of stdout is the path to REQUIRED_STATIC_FILES.zip; exits nonzero when
    the artifact is unavailable, so the playbook can fall back.
    """
    import argparse
    parser = argparse.ArgumentParser(description=main.__doc__)
    parser.add_argument("sha")
    parser.add_argument("dest_dir")
    args = parser.parse_args(argv)
    token = os.environ.get("GITHUB_TOKEN")
    if not token:
        print("GITHUB_TOKEN is not set")
        return 1
    path = fetch_static_artifact(token, args.sha, args.dest_dir)
    if path is None:
        print("artifact unavailable")
        return 1
    print(path)
    return 0


if __name__ == "__main__":
    import sys
    sys.exit(main())
