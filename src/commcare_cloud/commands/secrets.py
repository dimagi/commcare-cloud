import getpass

import six
import yaml

from commcare_cloud.commands.command_base import CommandBase, Argument
from commcare_cloud.environment.main import get_environment


class Secrets(CommandBase):
    command = 'secrets'
    help = (
        "View and edit secrets through the CLI"
    )

    arguments = (
        Argument(dest='subcommand', choices=['view', 'edit']),
        Argument(dest='secret_name'),
    )

    def run(self, args, unknown_args):
        environment = get_environment(args.env_name)
        if args.subcommand == 'view':
            return self._secrets_view(environment, args.secret_name)
        if args.subcommand == 'edit':
            return self._secrets_edit(environment, args.secret_name)

    def _secrets_view(self, environment, secret_name):
        secret = environment.get_secret(secret_name)
        if isinstance(secret, six.string_types):
            print(secret)
        else:
            print(yaml.safe_dump(secret))

    def _secrets_edit(self, environment, secret_name):
        environment.secrets_backend.prompt_user_input()
        secret_value = getpass.getpass("New value for '{}' secret '{}': ".format(environment.name, secret_name))
        environment.secrets_backend.set_secret(secret_name, secret_value)
