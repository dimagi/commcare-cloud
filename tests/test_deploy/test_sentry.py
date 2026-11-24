from unittest.mock import Mock

from commcare_cloud.commands.deploy.deploy_diff import DeployDiff
from commcare_cloud.commands.deploy.sentry import get_release_commits


def test_get_release_commits_without_current_commit():
    repo = Mock()
    diff = DeployDiff(repo, None, "def456", None)

    assert get_release_commits(diff) is None
    repo.compare.assert_not_called()
