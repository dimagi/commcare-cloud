import os
from getpass import getpass
from pathlib import Path

from github import Github

from commcare_cloud.colors import color_warning, color_notice
from commcare_cloud.commands.command_base import CommandError

PROJECT_ROOT = Path(__file__).parent
GITHUB_TOKEN = None


class GithubException(CommandError):
    pass


def github_repo(repo_name, repo_is_private=False, require_write_permissions=False):
    # optimistically get the token to get higher rate limit from Github
    token, _ = get_github_credentials_no_prompt()
    if not token and (repo_is_private or require_write_permissions):
        token = get_github_credentials(repo_name, repo_is_private, require_write_permissions)
        if not token:
            raise GithubException("Github token is required.")

    repo = Github(login_or_token=token).get_repo(repo_name)
    if require_write_permissions and not (repo.permissions and repo.permissions.push):
        raise GithubException(f"Supplied token does not have write permissions for '{repo_name}'")
    return repo


def get_github_credentials(repo_name, repo_is_private, require_write_permissions):
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
        private = "private " if repo_is_private else ""
        print(f"Github token is required for {private}repository {repo_name}.")
        if require_write_permissions:
            print("The token must have write permissions to the repository to create release tags.")
        print(
            "\nYou can add a config file to automate this step:\n"
            f"    $ cp {PROJECT_ROOT}/config.example.py {PROJECT_ROOT}/config.py\n"
            f"Then edit {PROJECT_ROOT}/config.py"
        )
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
