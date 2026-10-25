from unittest.mock import Mock, patch

import pytest

from commcare_cloud.commands.deploy.deploy_diff import DeployDiff


@pytest.mark.parametrize("template_name", [
    "console.txt.j2",
    "email.html.j2",
    "slack.md.j2",
])
def test_render_diff_with_warnings(template_name):
    diff = DeployDiff(Mock(), None, "abc123", Mock())
    context = {
        "new_version_details": {},
        "errors": [],
        "warnings": ["Insufficient info to get deploy diff."],
        "changelogs": {"changelogs": [], "error": False},
        "maintenance_prs": {"maintenance_prs": [], "error": False},
    }
    with patch.object(DeployDiff, "get_diff_context", return_value=context):
        rendered = diff.render_diff(template_name)
    assert "Insufficient info to get deploy diff." in rendered
