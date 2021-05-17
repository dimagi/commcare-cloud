import getpass
import os

import six
from memoized import memoized


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
