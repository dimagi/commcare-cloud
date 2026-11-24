import tempfile
from unittest.mock import patch

import pytest
from cryptography.fernet import Fernet
from unmagic import fixture

from commcare_cloud.ansible.plugins.lookup import cchq_aws_secret as plugin


@fixture
def inventory_dir():
    # The secrets cache is written under the inventory directory, encrypted
    # with a key that commcare-cloud generates for each run.
    env = {
        "AWS_REGION": "us-east-1",
        "AWS_SECRETS_CACHE_KEY": Fernet.generate_key().decode(),
    }
    with tempfile.TemporaryDirectory() as path, patch.dict("os.environ", env):
        yield path


@fixture
def upstream_run():
    # Patch the amazon.aws lookup, which would call AWS Secrets Manager.
    base = plugin.secretsmanager_secret.LookupModule
    with patch.object(base, "run", autospec=True) as run:
        yield run


def lookup(term, **kwargs):
    variables = {"inventory_dir": inventory_dir()}
    return plugin.LookupModule().run([term], variables, **kwargs)


@inventory_dir
@upstream_run
def test_returns_json_decoded_value():
    upstream_run().return_value = ['{"user": "cchq"}']

    assert lookup("commcare-staging/COUCH") == [{"user": "cchq"}]


@inventory_dir
@upstream_run
def test_region_defaults_to_aws_region_env_var():
    upstream_run().return_value = ['"x"']

    lookup("commcare-staging/COUCH")

    _self, terms, _variables = upstream_run().call_args.args
    assert terms == ["commcare-staging/COUCH"]
    assert upstream_run().call_args.kwargs == {"region": "us-east-1"}


@inventory_dir
@upstream_run
def test_explicit_region_is_kept():
    upstream_run().return_value = ['"x"']

    lookup("commcare-staging/COUCH", region="eu-west-1")

    assert upstream_run().call_args.kwargs == {"region": "eu-west-1"}


@inventory_dir
@upstream_run
def test_second_lookup_uses_cache():
    upstream_run().return_value = ['"secret"']

    assert lookup("commcare-staging/COUCH") == ["secret"]
    assert lookup("commcare-staging/COUCH") == ["secret"]
    assert upstream_run().call_count == 1


@inventory_dir
@upstream_run
def test_lookups_of_different_secrets_are_cached_separately():
    upstream_run().side_effect = [['"one"'], ['"two"']]

    assert lookup("commcare-staging/ONE") == ["one"]
    assert lookup("commcare-staging/TWO") == ["two"]
    assert lookup("commcare-staging/ONE") == ["one"]
    assert upstream_run().call_count == 2


@inventory_dir
@upstream_run
def test_error_is_cached_and_raised():
    upstream_run().side_effect = RuntimeError("access denied")

    with pytest.raises(RuntimeError, match="access denied"):
        lookup("commcare-staging/COUCH")
    with pytest.raises(RuntimeError, match="access denied"):
        lookup("commcare-staging/COUCH")
    assert upstream_run().call_count == 1
