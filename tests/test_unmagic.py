import pytest
from unmagic.fence import is_fenced


@pytest.mark.parametrize("module", [
    "commcare_cloud",
    "commcare_cloud.commands",

    "test_postgresql_units",  # in src/commcare_cloud/commands/terraform/tests, which has no __init__.py

    "tests",
    "tests.test_deploy",
])
def test_fence(module):
    def func():
        ...

    func.__module__ = module

    assert is_fenced(func)
