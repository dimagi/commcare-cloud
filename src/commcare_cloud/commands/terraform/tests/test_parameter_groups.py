from nose.tools import assert_raises

from commcare_cloud.environment.schemas.terraform import RdsParameterGroupConfig
from commcare_cloud.commands.terraform.terraform import validate_references_to_parameter_groups


def _make_group(name, family, params):
    data = {"name": name, "family": family, "params": params}
    return RdsParameterGroupConfig.wrap(data)


def test_validate_references_to_parameter_groups():
    # assert valid reference
    validate_references_to_parameter_groups(
        {"pg18-params": _make_group("pg18-params", "postgres18", {})},
        [type("Instance", (), {"identifier": "pg0", "parameter_group": "pg18-params"})],
    )

    # assert invalid reference
    with assert_raises(ValueError) as context:
        validate_references_to_parameter_groups(
            {},
            [type("Instance", (), {"identifier": "pg0", "parameter_group": "nonexistent"})],
        )
        message = str(context.exception)
        assert "pg0" in message
        assert "nonexistent" in message

    # assert parameter_group not required
    validate_references_to_parameter_groups(
        {},
        [type("Instance", (), {"identifier": "pg0", "parameter_group": None})],
    )
