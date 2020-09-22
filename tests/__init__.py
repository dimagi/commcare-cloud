from __future__ import absolute_import
from __future__ import unicode_literals
from mock import patch

from commcare_cloud.commands.terraform.aws import StringIsGuess


def setup_package():
    global patches
    patches = [
        patch.dict("os.environ", COMMCARE_CLOUD_DEFAULT_USERNAME=""),
        # handle memoized decorator (in case get_default_username has already been called)
        patch(
            "commcare_cloud.commands.inventory_lookup.getinventory.get_default_username",
            lambda: StringIsGuess("", is_guess=True),
        ),

    ]
    for patch_ in patches:
        patch_.start()


def teardown_package():
    for patch_ in patches:
        patch_.stop()
