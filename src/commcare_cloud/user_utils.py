import getpass
import os

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
    environment = get_environment(env_name)
    username = default_username = get_default_username()
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
        print_help_message_about_the_commcare_cloud_default_username_env_var(username)
    return username


def print_help_message_about_the_commcare_cloud_default_username_env_var(username):
    puts(color_notice("Did you know? You can put"))
    puts(color_notice("    export COMMCARE_CLOUD_DEFAULT_USERNAME={}".format(username)))
    puts(color_notice("in your profile to never have to type that in again! 🌈"))
