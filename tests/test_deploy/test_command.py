# Tests for commcare_cloud.commands.deploy.command.Deploy
# Way too many things are mocked here.
import sys
from datetime import datetime
from pathlib import Path
from unittest.mock import Mock, patch

import pytest
from github.GithubException import UnknownObjectException

from commcare_cloud.commands.deploy import command, commcare
from commcare_cloud.commands.deploy.deploy_diff import DeployDiff
from commcare_cloud.commands.deploy.private_repo import PrivateRepoError, PrivateRevision
from commcare_cloud.commands.deploy.utils import DeployContext
from commcare_cloud.commands import preindex_views
from commcare_cloud.commcare_cloud import call_commcare_cloud
from commcare_cloud.environment.main import Environment, get_environment
from commcare_cloud.environment.schemas.fab_settings import FabSettingsConfig

PRIVATE_URL = "git@github.com:o/p.git"
PRIVATE_SHA = "f" * 40


def test_deploy_commcare_happy_path():
    def run_playbook(playbook, context, *args, unknown_args={}, **kw):
        assert unknown_args == ["-e", "code_version=def456"]
        assert context.environment.release_name == "2020-01-02_03.04"
        log.append(playbook)
        return 0

    log = []
    with patch.multiple(
        commcare,
        record_deploy_failed=Mock(),
        record_deploy_start=Mock(),
        record_successful_deploy=Mock(),
        run_ansible_playbook=run_playbook,
    ):
        _deploy_commcare()

    assert log == ["deploy_hq.yml"]


def test_resume_deploy_with_release_name():
    def run_playbook(playbook, context, *args, unknown_args=None, **kw):
        assert unknown_args == ["-e", "code_version=def456"]
        assert context.environment.release_name == "FRANK"
        log.append(playbook)
        return 0

    log = []
    with patch.multiple(
        commcare,
        record_deploy_failed=Mock(),
        record_deploy_start=Mock(),
        record_successful_deploy=Mock(),
        run_ansible_playbook=run_playbook,
    ):
        _deploy_commcare("--resume=FRANK")

    assert log == ["deploy_hq.yml"]


def test_resume_deploy_without_release_name_raises():
    def run_playbook(playbook, context, *args, unknown_args=None, **kw):
        raise Exception("unexpected")

    with (
        patch.object(commcare, "run_ansible_playbook", run_playbook),
        pytest.raises(SystemExit),
        patch("sys.stderr", sys.stdout)
    ):
        _deploy_commcare("--resume")


def test_deploy_limited_release():
    def run_playbook(playbook, context, *args, unknown_args=None, **kw):
        assert unknown_args == [
            "-e", "code_version=def456",
            "-e", "keep_until=2020-01-03_03.04",
            "--tags=private_release",
        ]
        assert context.environment.release_name == "2020-01-02_03.04"
        assert kw.get("limit") == "django_manage"
        log.append(playbook)
        return 0

    log = []
    with patch.multiple(
        commcare,
        datetime=fakedatetime,
        run_ansible_playbook=run_playbook,
    ):
        _deploy_commcare("--private")

    assert log == ["deploy_hq.yml"]


def test_deploy_limited_release_to_webworker():
    def run_playbook(playbook, context, *args, unknown_args=None, **kw):
        assert unknown_args == [
            "-e", "code_version=def456",
            "-e", "keep_until=2020-01-03_03.04",
            "--tags=private_release",
        ]
        assert context.environment.release_name == "2020-01-02_03.04"
        assert kw.get("limit") == "webworkers[0]"
        log.append(playbook)
        return 0

    log = []
    with patch.multiple(
        commcare,
        datetime=fakedatetime,
        run_ansible_playbook=run_playbook,
    ):
        _deploy_commcare("--private", "--limit=webworkers[0]")

    assert log == ["deploy_hq.yml"]


def test_deploy_private_release_to_all_applicable_hosts():
    def run_playbook(playbook, context, *args, unknown_args=None, **kw):
        assert unknown_args == [
            "-e", "code_version=def456",
            "-e", "keep_until=2020-01-03_03.04",
            "--tags=private_release",
        ]
        assert context.environment.release_name == "2020-01-02_03.04"
        assert kw.get("limit") == "all"
        log.append(playbook)
        return 0

    log = []
    summary = []
    with patch.multiple(
        commcare,
        color_summary=summary.append,
        datetime=fakedatetime,
        run_ansible_playbook=run_playbook,
    ):
        _deploy_commcare("--private", "--limit=all")

    assert log == ["deploy_hq.yml"]
    assert summary == [
        "Your private release is located here:",
        "/home/cchq/www/small_cluster/releases/2020-01-02_03.04",
    ]


def test_deploy_limited_release_with_keep_days():
    def run_playbook(playbook, context, *args, unknown_args=None, **kw):
        assert unknown_args == [
            "-e", "code_version=def456",
            "-e", "keep_until=2020-01-12_03.04",
            "--tags=private_release",
        ]
        assert context.environment.release_name == "2020-01-02_03.04"
        assert kw.get("limit") == "django_manage"
        log.append(playbook)
        return 0

    log = []
    with patch.multiple(
        commcare,
        datetime=fakedatetime,
        run_ansible_playbook=run_playbook,
    ):
        _deploy_commcare("--private", "--keep-days=10")

    assert log == ["deploy_hq.yml"]


def test_preindex_views():
    def run_playbook(playbook, context, *args, unknown_args=None, **kw):
        assert unknown_args == [
            "-e", "code_version=def456",
            "-e", "keep_until=2020-01-03_03.04",
            "--tags=private_release",
        ]
        assert context.environment.release_name == "2020-01-02_03.04"
        assert kw.get("limit") == "pillowtop[0]"
        log.append(playbook)
        return 0

    def run_command(env_name, cmd, *args, **kw):
        assert not kw, kw
        log.append(" ".join((cmd,) + args))
        return 0

    log = []
    with (
        patch.object(preindex_views, "check_branch"),
        patch.object(preindex_views, "commcare_cloud", run_command),
        patch.object(preindex_views, "datetime", fakedatetime),
        patch.object(commcare, "run_ansible_playbook", run_playbook),
        patch.object(commcare, "datetime", fakedatetime),
    ):
        _deploy_commcare(cmd=("preindex-views",))

    assert log == [
        "deploy_hq.yml",
        "django-manage preindex_everything --server=pillowtop[0] --release=2020-01-02_03.04 --tmux --mail",
    ]


def test_deploy_private_repo_passes_repo_vars():
    def run_playbook(playbook, context, *args, unknown_args=None, **kw):
        assert unknown_args == [
            "-e", "code_version=def456",
            "-e", f"commcarehq_repository={PRIVATE_URL}",
            "-e", "use_private_code_repo=true",
        ]
        log.append(playbook)
        return 0

    log = []
    record_successful_deploy = Mock()
    with patch.multiple(
        commcare,
        _get_private_repo_url=Mock(return_value=PRIVATE_URL),
        record_deploy_failed=Mock(),
        record_deploy_start=Mock(),
        record_successful_deploy=record_successful_deploy,
        run_ansible_playbook=run_playbook,
    ):
        _deploy_commcare("--private-repo", "--commcare-rev=b")

    assert log == ["deploy_hq.yml"]
    [(env, context), _] = record_successful_deploy.call_args
    assert context.get_meta_value("code_repo") == "o/p"


def test_deploy_private_repo_with_private_release():
    def run_playbook(playbook, context, *args, unknown_args=None, **kw):
        assert unknown_args == [
            "-e", "code_version=def456",
            "-e", f"commcarehq_repository={PRIVATE_URL}",
            "-e", "use_private_code_repo=true",
            "-e", "keep_until=2020-01-03_03.04",
            "--tags=private_release",
        ]
        assert kw.get("limit") == "django_manage"
        log.append(playbook)
        return 0

    log = []
    with patch.multiple(
        commcare,
        _get_private_repo_url=Mock(return_value=PRIVATE_URL),
        datetime=fakedatetime,
        run_ansible_playbook=run_playbook,
    ):
        _deploy_commcare("--private", "--private-repo", "--commcare-rev=b")

    assert log == ["deploy_hq.yml"]


def test_deploy_private_repo_without_setting_exits():
    record_deploy_start = Mock()
    run_playbook = Mock()
    with (
        patch.multiple(
            commcare,
            record_deploy_start=record_deploy_start,
            run_ansible_playbook=run_playbook,
        ),
        pytest.raises(SystemExit) as exc,
    ):
        _deploy_commcare("--private-repo", "--commcare-rev=b")

    assert "private_code_repo" in str(exc.value)
    assert "small_cluster/fab-settings.yml" in str(exc.value)
    record_deploy_start.assert_not_called()
    run_playbook.assert_not_called()


def test_deploy_private_repo_unresolvable_rev_exits_before_recording():
    record_deploy_start = Mock()
    run_playbook = Mock()
    with (
        patch.object(FabSettingsConfig, "private_code_repo", PRIVATE_URL),
        patch.multiple(
            commcare,
            github_repo=Mock(),
            get_deployed_version=Mock(return_value="abc123"),
            resolve_private_revision=Mock(side_effect=PrivateRepoError("Could not fetch 'b'")),
            record_deploy_start=record_deploy_start,
            run_ansible_playbook=run_playbook,
        ),
        pytest.raises(SystemExit) as exc,
    ):
        _deploy_commcare("--private-repo", "--commcare-rev=b", diff=None)

    assert "Could not fetch 'b'" in str(exc.value)
    record_deploy_start.assert_not_called()
    run_playbook.assert_not_called()


def test_deploy_private_repo_requires_commcare_rev():
    get_url = Mock()
    record_deploy_start = Mock()
    run_playbook = Mock()
    confirm = Mock(return_value=True)
    with (
        patch.multiple(
            commcare,
            _get_private_repo_url=get_url,
            record_deploy_start=record_deploy_start,
            run_ansible_playbook=run_playbook,
        ),
        pytest.raises(SystemExit) as exc,
    ):
        _deploy_commcare("--private-repo", confirm_deploy=confirm)

    assert "--private-repo requires --commcare-rev" in str(exc.value)
    get_url.assert_not_called()
    confirm.assert_not_called()
    record_deploy_start.assert_not_called()
    run_playbook.assert_not_called()


def test_resume_private_repo_does_not_require_commcare_rev():
    def run_playbook(playbook, context, *args, unknown_args=None, **kw):
        assert "use_private_code_repo=true" in unknown_args
        log.append(playbook)
        return 0

    log = []
    with patch.multiple(
        commcare,
        _get_private_repo_url=Mock(return_value=PRIVATE_URL),
        get_deployed_version=Mock(return_value="abc123"),
        record_deploy_failed=Mock(),
        record_deploy_start=Mock(),
        record_successful_deploy=Mock(),
        run_ansible_playbook=run_playbook,
    ):
        _deploy_commcare("--private-repo", "--resume=2020-01-02_03.04")

    assert log == ["deploy_hq.yml"]


def test_deploy_diff_private_repo_requires_commcare_rev():
    resolve = Mock()
    print_diff = Mock()
    with (
        patch.object(commcare, "resolve_private_revision", resolve),
        patch.object(DeployDiff, "print_deployer_diff", print_diff),
        pytest.raises(SystemExit) as exc,
    ):
        _deploy_commcare("--private-repo", cmd=("deploy-diff",), diff=None)

    assert "--private-repo requires --commcare-rev" in str(exc.value)
    resolve.assert_not_called()
    print_diff.assert_not_called()


def test_get_code_diff_with_private_repo():
    resolve = Mock(return_value=PrivateRevision(PRIVATE_SHA, "base456", 2))
    diff = _get_code_diff_with(resolve, deployed_is_public=True, private_repo=True)

    resolve.assert_called_once_with(PRIVATE_URL, "b", "master")
    assert diff.deploy_commit == PRIVATE_SHA
    assert diff.current_commit == "abc123"
    assert (diff.compare_base, diff.compare_head) == ("abc123", "base456")
    assert diff.new_version_details["Branch deployed"] == "commcare: b (o/p)"
    assert diff.private_commit_count == 2


def test_get_code_diff_with_private_repo_over_private_deploy():
    def resolve(url, rev, branch):
        return {
            "b": PrivateRevision(PRIVATE_SHA, "base456", 1),
            "abc123": PrivateRevision("abc123", "base123", 1),
        }[rev]
    diff = _get_code_diff_with(resolve, deployed_is_public=False, private_repo=True)

    assert (diff.compare_base, diff.compare_head) == ("base123", "base456")


def test_get_code_diff_after_private_deploy():
    resolve = Mock(return_value=PrivateRevision("abc123", "base123", 1))
    diff = _get_code_diff_with(resolve, deployed_is_public=False)

    resolve.assert_called_once_with(PRIVATE_URL, "abc123", "master")
    assert diff.deploy_commit == "def456"
    assert (diff.compare_base, diff.compare_head) == ("base123", "def456")
    assert diff.private_commit_count == 0


def test_get_code_diff_after_private_deploy_without_access():
    resolve = Mock(side_effect=PrivateRepoError("Permission denied"))
    diff = _get_code_diff_with(resolve, deployed_is_public=False)

    assert (diff.compare_base, diff.compare_head) == ("abc123", "def456")


def test_get_code_diff_without_private_code_repo_setting():
    resolve = Mock()
    diff = _get_code_diff_with(resolve, deployed_is_public=False, private_code_repo=None)

    resolve.assert_not_called()
    assert (diff.compare_base, diff.compare_head) == ("abc123", "def456")
    assert diff.new_version_details["Branch deployed"] == "commcare: b"


def test_deploy_diff_command_private_repo():
    resolve = Mock(return_value=PrivateRevision(PRIVATE_SHA, "base456", 1))
    diffs = []
    with (
        patch.object(FabSettingsConfig, "private_code_repo", PRIVATE_URL),
        patch.object(commcare, "resolve_private_revision", resolve),
        patch.object(commcare, "github_repo", Mock()),
        patch.object(commcare, "get_deployed_version", lambda env: "abc123"),
        patch.object(DeployDiff, "print_deployer_diff", lambda self: diffs.append(self)),
    ):
        _deploy_commcare("--private-repo", "--commcare-rev=b", cmd=("deploy-diff",), diff=None)

    [diff] = diffs
    assert diff.deploy_commit == PRIVATE_SHA
    assert diff.compare_head == "base456"


def test_deploy_diff_command_with_commcare_rev():
    public = Mock()
    public.get_commit.return_value.sha = "def456"
    diffs = []
    with (
        patch.object(commcare, "github_repo", Mock(return_value=public)),
        patch.object(commcare, "get_deployed_version", lambda env: "abc123"),
        patch.object(DeployDiff, "print_deployer_diff", lambda self: diffs.append(self)),
    ):
        _deploy_commcare("--commcare-rev=my-branch", cmd=("deploy-diff",), diff=None)

    public.get_commit.assert_any_call("my-branch")
    [diff] = diffs
    assert diff.deploy_commit == "def456"


def test_deploy_formplayer_only_with_private_repo_exits():
    deploy_commcare = Mock()
    deploy_formplayer = Mock()
    with (
        patch.object(command, "deploy_commcare", deploy_commcare),
        patch.object(command, "deploy_formplayer", deploy_formplayer),
        pytest.raises(SystemExit) as exc,
    ):
        _deploy_commcare("--private-repo", cmd=("deploy", "formplayer"))

    assert "--private-repo only applies to the commcare component" in str(exc.value)
    deploy_commcare.assert_not_called()
    deploy_formplayer.assert_not_called()


def test_deploy_diff_formplayer_with_private_repo_exits():
    get_formplayer_diff = Mock()
    with (
        patch.object(command, "get_formplayer_deploy_diff", get_formplayer_diff),
        pytest.raises(SystemExit) as exc,
    ):
        _deploy_commcare("--private-repo", cmd=("deploy-diff", "formplayer"))

    assert "--private-repo only applies to the commcare component" in str(exc.value)
    get_formplayer_diff.assert_not_called()


def test_private_repo_not_github_url_exits():
    env = _get_test_environment()
    with (
        patch.object(FabSettingsConfig, "private_code_repo", "git@gitlab.com:o/p.git"),
        pytest.raises(SystemExit) as exc,
    ):
        commcare._get_private_repo_url(env)

    assert "private_code_repo" in str(exc.value)
    assert "git@gitlab.com:o/p.git" in str(exc.value)


def test_release_tag_goes_to_private_repo():
    env = _get_test_environment()
    context = DeployContext("CommCare HQ", "b", Mock(), datetime(2020, 1, 2))
    context.set_meta_value("code_repo", "o/p")
    create_release_tag = Mock()
    with patch.multiple(
        commcare,
        create_release_tag=create_release_tag,
        update_sentry_post_deploy=Mock(),
        announce_deploy_success=Mock(),
        call_record_deploy_success=Mock(),
        publish_deploy_event=Mock(),
    ):
        commcare.record_successful_deploy(env, context)

    create_release_tag.assert_called_once_with(env, "o/p", context.diff)


def _get_code_diff_with(resolve, deployed_is_public, private_repo=False, private_code_repo=PRIVATE_URL):
    env = _get_test_environment()
    public = Mock()

    def get_commit(sha):
        if sha == "abc123" and not deployed_is_public:
            raise UnknownObjectException(404, {"message": "Not Found"}, {})
        return Mock(sha="def456")
    public.get_commit.side_effect = get_commit
    with (
        patch.object(FabSettingsConfig, "private_code_repo", private_code_repo),
        patch.object(commcare, "resolve_private_revision", resolve),
        patch.object(commcare, "github_repo", Mock(return_value=public)),
        patch.object(commcare, "get_deployed_version", lambda env: "abc123"),
        patch.object(commcare, "DEPLOY_DIFF", None),
    ):
        diff = commcare._get_code_diff(env, {"commcare": "b"}, False, private_repo=private_repo)
    assert diff.repo is public
    return diff


def _deploy_commcare(*argv, cmd=("deploy", "commcare"), confirm_deploy=lambda *a: True, diff=...):
    if diff is ...:
        diff = DeployDiff(None, "abc123", "def456", None)
    get_environment.reset_cache()
    with (
        patch("commcare_cloud.environment.paths.ENVIRONMENTS_DIR", TEST_ENVS),
        patch.object(command, "check_branch"),
        patch.object(command, "datetime", fakedatetime),
        patch.object(commcare, "confirm_deploy", confirm_deploy),
        patch.object(commcare, "DEPLOY_DIFF", diff),
        patch.object(Environment, "_create_generated_yml", lambda self: None),
    ):
        argv = ("cchq", "small_cluster") + cmd + argv
        try:
            call_commcare_cloud(argv)
        finally:
            get_environment.reset_cache()


def _get_test_environment():
    get_environment.reset_cache()
    with patch("commcare_cloud.environment.paths.ENVIRONMENTS_DIR", TEST_ENVS):
        try:
            return get_environment("small_cluster")
        finally:
            get_environment.reset_cache()


TEST_ENVS = Path(__file__).parent.parent / "test_envs"


class fakedatetime:
    def utcnow():
        return datetime(2020, 1, 2, 3, 4)
