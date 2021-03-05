from __future__ import absolute_import
from __future__ import print_function
from __future__ import unicode_literals
import getpass
import json

import six
import yaml
from clint.textui import puts
from six.moves import input

from commcare_cloud.colors import color_error
from commcare_cloud.commands.command_base import CommandBase, Argument
from commcare_cloud.environment.main import get_environment
from commcare_cloud.environment.secrets.backends import all_secrets_backends_by_name
from commcare_cloud.environment.secrets.secrets_schema import get_known_secret_specs


class Secrets(CommandBase):
    command = 'secrets'
    help = (
        "View and edit secrets through the CLI"
    )

    arguments = (
        Argument(dest='subcommand', choices=['view', 'edit', 'list-append', 'list-remove']),
        Argument(dest='secret_name'),
    )

    def run(self, args, unknown_args):
        environment = get_environment(args.env_name)
        if args.subcommand == 'view':
            return self._secrets_view(environment, args.secret_name)
        if args.subcommand == 'edit':
            return self._secrets_edit(environment, args.secret_name)
        if args.subcommand == 'list-append':
            return self._secrets_append_to_list(environment, args.secret_name)
        if args.subcommand == 'list-remove':
            return self._secrets_remove_from_list(environment, args.secret_name)

    def _secrets_view(self, environment, secret_name):
        secret = environment.get_secret(secret_name)
        if isinstance(secret, six.string_types):
            print(secret)
        else:
            print(yaml.safe_dump(secret))

    def _secrets_edit(self, environment, secret_name):
        environment.secrets_backend.prompt_user_input()
        secret_value = getpass.getpass(f"New value for '{environment.name}' secret '{secret_name}': ")
        try:
            secret_value = json.loads(secret_value)
        except ValueError:
            pass
        environment.secrets_backend.set_secret(secret_name, secret_value)

    def _secrets_append_to_list(self, environment, secret_name):
        secret = environment.get_secret(secret_name)
        if not isinstance(secret, list):
            print(f"Cannot append. '{secret_name}' is not a list.")
            exit(-1)
        value_to_append = getpass.getpass(f"Value for '{environment.name}' to append to '{secret_name}': ")
        secret.append(value_to_append)
        environment.secrets_backend.set_secret(secret_name, secret)

    def _secrets_remove_from_list(self, environment, secret_name):
        secret = environment.get_secret(secret_name)
        if not isinstance(secret, list):
            print(f"Cannot remove. '{secret_name}' is not a list.")
            exit(-1)
        value_to_remove = getpass.getpass(f"Value for '{environment.name}' to remove from '{secret_name}': ")
        try:
            secret.remove(value_to_remove)
        except ValueError:
            print(f"Value not found in list.")
            exit(-1)
        environment.secrets_backend.set_secret(secret_name, secret)


class MigrateSecrets(CommandBase):
    command = 'migrate-secrets'
    help = (
        "Migrate secrets from one backend to another"
    )

    arguments = (
        Argument(dest='from_backend'),
    )

    def run(self, args, unknown_args):
        environment = get_environment(args.env_name)
        from_backend = all_secrets_backends_by_name[args.from_backend].from_environment(environment)
        to_backend = environment.secrets_backend
        if from_backend.name == to_backend.name:
            puts(color_error(
                'Refusing to copy from {from_backend.name} to {to_backend.name}: backends must differ'
                .format(from_backend=from_backend, to_backend=to_backend)
            ))
            exit(-1)

        print("Copying data from {from_backend.name} to {to_backend.name}:".format(
            from_backend=from_backend, to_backend=to_backend))
        for secret_spec in get_known_secret_specs():
            try:
                secret_value = from_backend.get_secret(secret_spec.name)
            except KeyError:
                print("No value for {secret_spec.name}... Skipping".format(secret_spec=secret_spec))
                continue
            to_backend.set_secret(secret_spec.name, secret_value)
            print("Copied value for {secret_spec.name}".format(secret_spec=secret_spec))
