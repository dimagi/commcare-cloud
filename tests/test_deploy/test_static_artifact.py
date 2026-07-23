import io
import zipfile
from pathlib import Path

import pytest
import requests_mock
from unittest.mock import patch

from commcare_cloud.commands.deploy.static_artifact import (
    ARTIFACTS_URL,
    RUNS_URL,
    fetch_static_artifact,
)

pytestmark = pytest.mark.filterwarnings("ignore:.*used magic fixture.*:UserWarning")

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
    with requests_mock.Mocker() as m, patch("time.sleep") as sleep:
        m.get(LIST_URL, [
            {"json": NOT_FOUND},
            {"json": NOT_FOUND},
            {"json": _found_response()},
        ])
        m.get(RUNS_QUERY_URL, json=_runs_response("in_progress"))
        m.get(DOWNLOAD_URL, content=_outer_zip())
        result = fetch_static_artifact("tok", SHA, str(tmp_path))
    assert result is not None
    assert [c.args[0] for c in sleep.call_args_list] == [30, 30]


def test_no_workflow_run_fails_fast(tmp_path):
    with requests_mock.Mocker() as m, patch("time.sleep") as sleep:
        m.get(LIST_URL, json=NOT_FOUND)
        m.get(RUNS_QUERY_URL, json={"workflow_runs": []})
        result = fetch_static_artifact("tok", SHA, str(tmp_path))
    assert result is None
    sleep.assert_not_called()  # no waiting when there is no build to wait for
    assert m.call_count == 2  # one artifact check + one run check


def test_failed_build_fails_fast(tmp_path):
    with requests_mock.Mocker() as m, patch("time.sleep") as sleep:
        m.get(LIST_URL, json=NOT_FOUND)
        m.get(RUNS_QUERY_URL, json=_runs_response("completed", "failure"))
        result = fetch_static_artifact("tok", SHA, str(tmp_path))
    assert result is None
    sleep.assert_not_called()


def test_completed_build_rechecks_artifact_once(tmp_path):
    # Build finished successfully between our artifact check and run check:
    # one final artifact lookup catches it.
    with requests_mock.Mocker() as m, patch("time.sleep"):
        m.get(LIST_URL, [{"json": NOT_FOUND}, {"json": _found_response()}])
        m.get(RUNS_QUERY_URL, json=_runs_response("completed", "success"))
        m.get(DOWNLOAD_URL, content=_outer_zip())
        result = fetch_static_artifact("tok", SHA, str(tmp_path))
    assert result is not None


def test_build_still_running_at_timeout_returns_none(tmp_path):
    with requests_mock.Mocker() as m, patch("time.sleep"):
        m.get(LIST_URL, json=NOT_FOUND)
        m.get(RUNS_QUERY_URL, json=_runs_response("in_progress"))
        result = fetch_static_artifact(
            "tok", SHA, str(tmp_path), timeout=60, interval=30)
    assert result is None
    # waited 30, 60 -> ceiling reached after 2 sleeps; 3 artifact checks + 3 run checks
    assert m.call_count == 6


def test_expired_artifact_is_ignored(tmp_path):
    expired = {"total_count": 1, "artifacts": [
        {"id": 5, "name": f"staticfiles-{SHA}", "expired": True,
         "archive_download_url": DOWNLOAD_URL},
    ]}
    with requests_mock.Mocker() as m, patch("time.sleep"):
        m.get(LIST_URL, json=expired)
        m.get(RUNS_QUERY_URL, json={"workflow_runs": []})
        result = fetch_static_artifact("tok", SHA, str(tmp_path))
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
