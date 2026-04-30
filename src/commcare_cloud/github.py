import os
from getpass import getpass
from pathlib import Path

from github import Github

from commcare_cloud.colors import color_warning, color_notice

PROJECT_ROOT = Path(__file__).parent
GITHUB_KNOWN_HOSTS = PROJECT_ROOT / "github_known_hosts"
GITHUB_TOKEN = None


def github_repo(repo_name, prompt_if_missing=False):
    # optimistically get the token to get higher rate limit from Github
    token, _ = get_github_credentials_no_prompt()
    if not token and prompt_if_missing:
        token = get_github_credentials(repo_name)
    return Github(login_or_token=token).get_repo(repo_name)


def get_github_credentials(repo_name):
    global GITHUB_TOKEN

    token, found_in_legacy_location = get_github_credentials_no_prompt()

    if found_in_legacy_location:
        print(color_notice(f"[Deprecation Warning] Config file has moved."))
        print(color_notice(f"New location is {PROJECT_ROOT}/config.py or else use the "
                           f"'GITHUB_TOKEN' environment variable."))
        print(color_notice(f"\nYou can move the config to the new location as follows:"))
        print(color_notice(f"    $ mv {PROJECT_ROOT}/fab/config.py {PROJECT_ROOT}/config.py\n"))

    if token is None:
        print(color_warning("Github credentials not found!"))
        print(f"Github token is required for repository {repo_name}.")
        print(
            "\nYou can add a config file to automate this step:\n"
            f"    $ cp {PROJECT_ROOT}/config.example.py {PROJECT_ROOT}/config.py\n"
            f"Then edit {PROJECT_ROOT}/config.py"
        )
        print(color_notice(
            "To generate a GitHub access token, follow these instructions: https://github.com/blog/1509-personal-api-tokens\n"
            "For permissions choose repo > public_repo"
        ))
        token = getpass('Github Token: ')

    os.environ["GITHUB_TOKEN"] = token  # set in env for access by subprocesses
    GITHUB_TOKEN = token
    return token or None


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
        # check legacy location
        try:
            from .fab.config import GITHUB_APIKEY
            return GITHUB_APIKEY, True
        except ImportError:
            pass

    return None, False
