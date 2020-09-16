from __future__ import print_function
from __future__ import absolute_import
from __future__ import unicode_literals
from commcare_cloud.commands.command_base import CommandBase


class TestEnvironments(CommandBase):
    command = 'test-environments'
    help = "Run test environments"

    def run(self, args, unknown_args):
        import nose
        nose.runmodule('commcare_cloud.manage_commcare_cloud',
                       argv=['manage-commcare-cloud', '-v'])
