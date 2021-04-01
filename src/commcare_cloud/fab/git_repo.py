from getpass import getpass

from fabric.colors import red
from fabric.state import env
from github import Github
from memoized import memoized

from commcare_cloud.fab.const import PROJECT_ROOT

GITHUB_TOKEN = None


def _get_github_token(message, required=False):
    global GITHUB_TOKEN

    if GITHUB_TOKEN is not None:
        if GITHUB_TOKEN or not required:
            return GITHUB_TOKEN

    try:
        from .config import GITHUB_APIKEY
    except ImportError:
        print(red("Github credentials not found!"))
        print(message)
        print((
            "You can add a config file to automate this step:\n"
            "    $ cp {project_root}/config.example.py {project_root}/config.py\n"
            "Then edit {project_root}/config.py"
        ).format(project_root=PROJECT_ROOT))
        GITHUB_TOKEN = getpass('Github Token: ')
    else:
        GITHUB_TOKEN = GITHUB_APIKEY
    return GITHUB_TOKEN


def get_github_token(message=None, required=False):
    if not message:
        message = "This deploy script uses the Github API to display a summary of changes to be deployed."
        if getattr(env, "tag_deploy_commits", None):
            message += (
                "\nYou're deploying an environment which uses release tags. "
                "Provide Github auth details to enable release tags."
            )
    return _get_github_token(message, required)


@memoized
def get_github():
    token = get_github_token()
    return Github(login_or_token=token)


@memoized
def github_auth_provided():
    return bool(get_github_token())
