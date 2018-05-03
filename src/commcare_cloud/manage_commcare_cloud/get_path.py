from commcare_cloud.commands.command_base import CommandBase
from commcare_cloud.environment.paths import ANSIBLE_DIR


class GetPath(CommandBase):
    command = 'get-path'
    help = "Print the value of a property of the commcare-cloud install"

    def make_parser(self):
        self.parser.add_argument('property', choices=['ANSIBLE_DIR'])

    def run(self, args, unknown_args):
        if args.property == 'ANSIBLE_DIR':
            print(ANSIBLE_DIR)
