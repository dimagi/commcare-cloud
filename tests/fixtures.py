from unittest.mock import patch

from unmagic import fixture

from commcare_cloud.user_utils import StringIsGuess


@fixture(scope="package")
def package_patches():
    patches = [
        patch.dict("os.environ", COMMCARE_CLOUD_DEFAULT_USERNAME=""),
        # handle memoized decorator (in case get_default_username has already been called)
        patch(
            "commcare_cloud.user_utils.get_default_username",
            lambda: StringIsGuess("", is_guess=True),
        ),
    ]
    for patch_ in patches:
        patch_.start()
    try:
        yield
    finally:
        for patch_ in patches:
            patch_.stop()
