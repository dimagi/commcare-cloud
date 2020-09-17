from __future__ import print_function
from __future__ import absolute_import
from commcare_cloud.commands.command_base import CommandBase
from commcare_cloud.environment.paths import ANSIBLE_DIR, get_available_envs


def get_ANSIBLE_DIR():
    yield ANSIBLE_DIR


def get_commands():
    from commcare_cloud import commcare_cloud
    for command_type in commcare_cloud.COMMAND_TYPES:
        yield command_type.command
        for alias in command_type.aliases:
            yield alias


def get_environments():
    for env in get_available_envs():
        yield env


CHOICES = {
    'ANSIBLE_DIR': get_ANSIBLE_DIR,
    'commands': get_commands,
    'environments': get_environments,
}


class Get(CommandBase):
    command = 'get'
    help = "Print the value of a property of the commcare-cloud install"

    def make_parser(self):
        self.parser.add_argument('properties', choices=sorted(CHOICES), nargs='+')

    def run(self, args, unknown_args):
        for property in args.properties:
            print(' '.join(CHOICES[property]()))
