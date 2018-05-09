from __future__ import print_function
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
            var_keys[env] = set(recursive_keys(environment.get_vault_variables()))

        for env in envs:
            print('\t{}'.format(env), end='')
        print()
        for key in sorted(set(chain.from_iterable(var_keys.values()))):
            print('.'.join(part if part is not None else '*' for part in key), end='')
            for env in envs:
                print('\t{}'.format('x' if key in var_keys[env] else ''), end='')
            print()


def recursive_keys(o, path=()):
    if isinstance(o, dict):
        for key, value in o.items():
            for key_ in recursive_keys(value, path=path + (key,)):
                yield key_
    elif isinstance(o, list):
        for value in o:
            for key_ in recursive_keys(value, path=path + (None,)):
                yield key_
    else:
        yield path
