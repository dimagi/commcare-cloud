import getpass
import os
import subprocess

import six
from clint.textui import puts
from memoized import memoized

from commcare_cloud.colors import color_error, color_notice
from commcare_cloud.environment.main import get_environment


class StringIsGuess(six.text_type):
    def __new__(cls, *args, **kwargs):
        is_guess = kwargs.pop('is_guess')
        self = super(StringIsGuess, cls).__new__(cls, *args, **kwargs)
        self.is_guess = is_guess
        return self


@memoized
def get_default_username():
    """
    Returns a special string type that has field is_guess

    If is_guess is True, the caller should assume the user wants this value
    and should not give them a chance to change their choice of user interactively.
    """
    environ_username = os.environ.get('COMMCARE_CLOUD_DEFAULT_USERNAME')
    if environ_username:
        return StringIsGuess(environ_username, is_guess=False)
    else:
        return StringIsGuess(getpass.getuser(), is_guess=True)


def get_dev_username(env_name):
    """Get the configured username (OS or via env var) and verify it against
    the list of users configured in the environment."""
    username = get_default_username()
    return _check_username(env_name, username, COMMCARE_CLOUD_DEFAULT_USERNAME_ENV_VAR_MESSAGE)


COMMCARE_CLOUD_DEFAULT_USERNAME_ENV_VAR_MESSAGE = """
Did you know? You can put
    export COMMCARE_CLOUD_DEFAULT_USERNAME={username}
in your profile to never have to type that in again! 🌈
"""


def print_help_message_about_the_commcare_cloud_default_username_env_var(username):
    puts(color_notice(COMMCARE_CLOUD_DEFAULT_USERNAME_ENV_VAR_MESSAGE.format(username)))


@memoized
def get_default_ssh_username(host):
    """
    Returns a special string type that has field is_guess

    If is_guess is False, the caller should assume the user wants this value
    and should not give them a chance to change their choice of user interactively.
    """
    for line in subprocess.check_output(['ssh', host, '-G']).decode('utf8').splitlines():
        if line.startswith("user "):
            return StringIsGuess(line.split()[1], is_guess=False)
    return StringIsGuess(getpass.getuser(), is_guess=False)


DEFAULT_SSH_USERNAME_MESSAGE = """
Did you know? You can add this to you '~/.ssh/config' to set your username:

Host *
    User {username}
"""


def get_ssh_username(host, env_name):
    """Use `ssh -G <host>` to get the SSH username and verify it against
    the list of users configured in the environment."""
    username = get_default_ssh_username(host)
    return _check_username(env_name, username, DEFAULT_SSH_USERNAME_MESSAGE)


def _check_username(env_name, username, message):
    default_username = username
    environment = get_environment(env_name)
    while True:
        if not username or default_username.is_guess:
            username = input(f"Enter your SSH username ({default_username}): ")
            if not username:
                username = default_username
        if username in environment.users_config.dev_users.present:
            break
        allowed_users = environment.users_config.dev_users.present
        env_users = '\n  - '.join([''] + allowed_users)
        puts(color_error(
            f"Unauthorized user {username}.\n\n"
            f"Please pass in one of the allowed ssh users:{env_users}"
        ))
        username = ""
    if default_username.is_guess:
        print(color_notice(message.format(username)))
    return username
