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
    token = None
    if repo_is_private or require_write_permissions:
        token = get_github_credentials(repo_name, repo_is_private, require_write_permissions)

    repo = Github(login_or_token=token).get_repo(repo_name)
    if require_write_permissions and not (repo.permissions and repo.permissions.push):
        raise GithubException(f"Supplied token does not have write permissions for '{repo_name}'")
    return repo


def get_github_credentials(repo_name, repo_is_private, require_write_permissions):
    global GITHUB_TOKEN

    if GITHUB_TOKEN is None:
        GITHUB_TOKEN = os.environ.get("GITHUB_TOKEN")

    if GITHUB_TOKEN:
        return GITHUB_TOKEN

    try:
        from .config import GITHUB_APIKEY
    except ImportError:
        try:
            from .fab.config import GITHUB_APIKEY
        except ImportError:
            pass
        else:
            print(color_notice(f"[Deprecation Warning] Config file has moved."))
            print(color_notice(f"New location is {PROJECT_ROOT}/config.py or else use the "
                               f"'GITHUB_TOKEN' environment variable."))
            GITHUB_TOKEN = GITHUB_APIKEY
            return GITHUB_TOKEN
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
        GITHUB_TOKEN = getpass('Github Token: ')
        os.environ["GITHUB_TOKEN"] = GITHUB_TOKEN
    else:
        GITHUB_TOKEN = GITHUB_APIKEY
    return GITHUB_TOKEN
