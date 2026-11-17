from pathlib import Path

from commcare_cloud.commands.command_base import CommandBase


class TestEnvironments(CommandBase):
    command = 'test-environments'
    help = "Run test environments"

    def run(self, args, unknown_args):
        import pytest
        test_path = Path(__file__).parent / "tests/test_environments.py"
        return pytest.main(["-v", test_path])
