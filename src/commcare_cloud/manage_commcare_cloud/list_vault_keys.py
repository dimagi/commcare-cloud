from __future__ import print_function
from __future__ import absolute_import
from itertools import chain

from commcare_cloud.commands.command_base import CommandBase
from commcare_cloud.environment.main import get_environment
from commcare_cloud.environment.paths import get_available_envs


class ListVaultKeys(CommandBase):
    command = 'list-vault-keys'
    help = """
    Audit the structure of vault.yml files.

    A password will be required for each encrypted vault file in the env.
    """

    def run(self, args, unknown_args):
        envs = sorted(get_available_envs(exclude_symlinks=True))
        var_keys = {}
        for env in envs:
            print('[{}] '.format(env), end='')
            environment = get_environment(env)
            var_keys[env] = set(get_flat_list_of_keys(environment.get_vault_variables()))

        for env in envs:
            print('\t{}'.format(env), end='')
        print()
        for key in sorted(set(chain.from_iterable(list(var_keys.values())))):
            print('.'.join(part if part is not None else '*' for part in key), end='')
            for env in envs:
                print('\t{}'.format('x' if key in var_keys[env] else ''), end='')
            print()


def get_flat_list_of_keys(nested_config, path=()):
    if isinstance(nested_config, dict):
        for key, value in nested_config.items():
            for key_ in get_flat_list_of_keys(value, path=path + (key,)):
                yield key_
    elif isinstance(nested_config, list):
        for value in nested_config:
            for key_ in get_flat_list_of_keys(value, path=path + (None,)):
                yield key_
    else:
        yield path
