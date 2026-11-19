from unittest.mock import Mock, patch

from commcare_cloud.commands.deploy.deploy_diff import DeployDiff


def test_compare_defaults_to_deployed_commits():
    repo = Mock(html_url="https://github.com/dimagi/commcare-hq")
    diff = DeployDiff(repo, "abc", "def", None)

    assert diff.url == "https://github.com/dimagi/commcare-hq/compare/abc...def"
    diff.git_comparison
    repo.compare.assert_called_once_with("abc", "def")


def test_compare_commits_override_deployed_commits():
    repo = Mock(html_url="https://github.com/dimagi/commcare-hq")
    diff = DeployDiff(repo, "abc", "private", None, compare_commits=("abc", "base"))

    assert diff.url == "https://github.com/dimagi/commcare-hq/compare/abc...base"
    diff.git_comparison
    repo.compare.assert_called_once_with("abc", "base")
    assert diff.deploy_commit == "private"
    assert not diff.deployed_commit_matches_latest_commit


def test_url_label():
    assert DeployDiff(Mock(), "abc", "def", None).url_label == "Complete diff"


def test_url_label_with_private_commits():
    diff = DeployDiff(Mock(), "abc", "private", None, compare_commits=("abc", "base"), private_commit_count=2)
    assert diff.url_label == "Public changes only (excludes 2 private commits; deployed commit private)"


def test_rendered_compare_url_label():
    repo = Mock(html_url="https://github.com/dimagi/commcare-hq", permissions=None)
    environment = Mock(public_vars={})
    public = DeployDiff(repo, "abc", "def", environment, generate_diff=False)
    private = DeployDiff(repo, "abc", "private", environment, generate_diff=False,
                         compare_commits=("abc", "base"), private_commit_count=1)

    with (
        patch.object(DeployDiff, "get_changelog_context", Mock(return_value={"changelogs": [], "error": False})),
        patch.object(DeployDiff, "get_maintenance_pr_context", Mock(return_value={"maintenance_prs": []})),
    ):
        public_text = public.get_slack_diff()
        private_text = private.get_slack_diff()

    assert "Here's the complete diff on github: https://github.com/dimagi/commcare-hq/compare/abc...def" \
        in public_text
    assert (
        "Public changes only (excludes 1 private commit; deployed commit private): "
        "https://github.com/dimagi/commcare-hq/compare/abc...base"
    ) in private_text
