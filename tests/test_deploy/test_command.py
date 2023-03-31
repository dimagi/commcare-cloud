# Tests for commcare_cloud.commands.deploy.command.Deploy
# Way too many things are mocked here.
import sys
from datetime import datetime
from pathlib import Path
from unittest.mock import Mock, patch

from testil import assert_raises, eq

from commcare_cloud.commands.deploy import command, commcare
from commcare_cloud.commands.deploy.deploy_diff import DeployDiff
from commcare_cloud.commands import preindex_views
from commcare_cloud.commcare_cloud import call_commcare_cloud
from commcare_cloud.environment.main import Environment, get_environment


def test_deploy_commcare_happy_path():
    def run_playbook(playbook, context, *args, unknown_args={}, **kw):
        eq(unknown_args, ["-e", "code_version=def456"])
        eq(context.environment.release_name, "2020-01-02_03.04")
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

    eq(log, ["deploy_hq.yml"])


def test_resume_deploy_with_release_name():
    def run_playbook(playbook, context, *args, unknown_args=None, **kw):
        eq(unknown_args, [])
        eq(context.environment.release_name, "FRANK")
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

    eq(log, ["deploy_hq.yml"])


def test_resume_deploy_without_release_name_raises():
    def run_playbook(playbook, context, *args, unknown_args=None, **kw):
        raise Exception("unexpected")

    with (
        patch.object(commcare, "run_ansible_playbook", run_playbook),
        assert_raises(SystemExit),
        patch("sys.stderr", sys.stdout)
    ):
        _deploy_commcare("--resume")


def test_deploy_limited_release():
    def run_playbook(playbook, context, *args, unknown_args=None, **kw):
        eq(unknown_args, [
            "-e", "code_version=def456",
            "-e", "keep_until=2020-01-03_03.04",
            "--tags=private_release",
        ])
        eq(context.environment.release_name, "2020-01-02_03.04")
        eq(kw.get("limit"), "django_manage")
        log.append(playbook)
        return 0

    log = []
    with patch.multiple(
        commcare,
        datetime=fakedatetime,
        run_ansible_playbook=run_playbook,
    ):
        _deploy_commcare("--private")

    eq(log, ["deploy_hq.yml"])


def test_deploy_limited_release_to_webworker():
    def run_playbook(playbook, context, *args, unknown_args=None, **kw):
        eq(unknown_args, [
            "-e", "code_version=def456",
            "-e", "keep_until=2020-01-03_03.04",
            "--tags=private_release",
        ])
        eq(context.environment.release_name, "2020-01-02_03.04")
        eq(kw.get("limit"), "webworkers[0]")
        log.append(playbook)
        return 0

    log = []
    with patch.multiple(
        commcare,
        datetime=fakedatetime,
        run_ansible_playbook=run_playbook,
    ):
        _deploy_commcare("--private", "--limit=webworkers[0]")

    eq(log, ["deploy_hq.yml"])


def test_deploy_private_release_to_all_applicable_hosts():
    def run_playbook(playbook, context, *args, unknown_args=None, **kw):
        eq(unknown_args, [
            "-e", "code_version=def456",
            "-e", "keep_until=2020-01-03_03.04",
            "--tags=private_release",
        ])
        eq(context.environment.release_name, "2020-01-02_03.04")
        eq(kw.get("limit"), "all")
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

    eq(log, ["deploy_hq.yml"])
    eq(summary, [
        "Your private release is located here:",
        "/home/cchq/www/small_cluster/releases/2020-01-02_03.04",
    ])


def test_deploy_limited_release_with_keep_days():
    def run_playbook(playbook, context, *args, unknown_args=None, **kw):
        eq(unknown_args, [
            "-e", "code_version=def456",
            "-e", "keep_until=2020-01-12_03.04",
            "--tags=private_release",
        ])
        eq(context.environment.release_name, "2020-01-02_03.04")
        eq(kw.get("limit"), "django_manage")
        log.append(playbook)
        return 0

    log = []
    with patch.multiple(
        commcare,
        datetime=fakedatetime,
        run_ansible_playbook=run_playbook,
    ):
        _deploy_commcare("--private", "--keep-days=10")

    eq(log, ["deploy_hq.yml"])


def test_preindex_views():
    def run_playbook(playbook, context, *args, unknown_args=None, **kw):
        eq(unknown_args, [
            "-e", "code_version=def456",
            "-e", "keep_until=2020-01-03_03.04",
            "--tags=private_release",
        ])
        eq(context.environment.release_name, "2020-01-02_03.04")
        eq(kw.get("limit"), "pillowtop[0]")
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

    eq(log, [
        "deploy_hq.yml",
        "django-manage preindex_everything --server=pillowtop[0] --release=2020-01-02_03.04 --tmux --mail",
    ])


def _deploy_commcare(*argv, cmd=("deploy", "commcare")):
    envs = Path(__file__).parent.parent / "test_envs"
    diff = DeployDiff(None, "abc123", "def456", None)
    get_environment.reset_cache()
    with (
        patch("commcare_cloud.environment.paths.ENVIRONMENTS_DIR", envs),
        patch.object(command, "check_branch"),
        patch.object(command, "datetime", fakedatetime),
        patch.object(commcare, "confirm_deploy", lambda *a: True),
        patch.object(commcare, "DEPLOY_DIFF", diff),
        patch.object(Environment, "_create_generated_yml", lambda self:None),
    ):
        argv = ("cchq", "small_cluster") + cmd + argv
        try:
            call_commcare_cloud(argv)
        finally:
            get_environment.reset_cache()


class fakedatetime:
    def utcnow():
        return datetime(2020, 1, 2, 3, 4)
