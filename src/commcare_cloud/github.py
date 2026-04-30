import os
from getpass import getpass
from pathlib import Path

from github import Github
from memoized import memoized

from commcare_cloud.colors import color_notice

PROJECT_ROOT = Path(__file__).parent
GITHUB_KNOWN_HOSTS = PROJECT_ROOT / "github_known_hosts"


def github_repo(repo_name, prompt_if_missing=False):
    """Return the PyGithub Repository for ``repo_name``.

    The optional token authenticates API calls (5,000/hr instead of 60/hr
    unauthenticated, and unlocks repo permissions metadata used by deploy
    diff). When ``prompt_if_missing`` is True and no token is found via
    env or config, ask interactively. Empty input continues unauthenticated.
    """
    token = get_github_credentials_no_prompt()
    if not token and prompt_if_missing:
        token = _prompt_for_github_token()
    return Github(login_or_token=token).get_repo(repo_name)


@memoized
def _warn_legacy_location():
    print(color_notice(f"[Deprecation Warning] Config file has moved."))
    print(color_notice(f"New location is {PROJECT_ROOT}/config.py or else use the "
                       f"'GITHUB_TOKEN' environment variable."))
    print(color_notice(f"\nYou can move the config to the new location as follows:"))
    print(color_notice(f"    $ mv {PROJECT_ROOT}/fab/config.py {PROJECT_ROOT}/config.py\n"))


@memoized
def _prompt_for_github_token():
    print(color_notice(
        "GitHub token not found. A token is recommended so the deploy diff "
        "can show PR details (titles, labels, authors). Read-only scope is "
        "sufficient — no write permissions needed."
    ))
    print(color_notice(
        "Generate a token at https://github.com/settings/tokens "
        "(scope: public_repo)."
    ))
    return getpass("Github token (or Enter to continue without): ") or None


@memoized
def get_github_credentials_no_prompt():
    token = os.environ.get("GITHUB_TOKEN")
    if token:
        return token

    try:
        from .config import GITHUB_APIKEY
        return GITHUB_APIKEY
    except ImportError:
        pass

    try:
        from .fab.config import GITHUB_APIKEY
    except ImportError:
        return None

    if GITHUB_APIKEY:
        _warn_legacy_location()
    return GITHUB_APIKEY
