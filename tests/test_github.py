import pytest

from commcare_cloud.github import github_full_name


@pytest.mark.parametrize("url", [
    "git@github.com:dimagi-commcare/private-commcare-hq.git",
    "https://github.com/dimagi-commcare/private-commcare-hq.git",
    "https://github.com/dimagi-commcare/private-commcare-hq",
])
def test_github_full_name(url):
    assert github_full_name(url) == "dimagi-commcare/private-commcare-hq"


def test_github_full_name_rejects_non_github():
    with pytest.raises(ValueError):
        github_full_name("git@gitlab.com:foo/bar.git")
