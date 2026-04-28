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
