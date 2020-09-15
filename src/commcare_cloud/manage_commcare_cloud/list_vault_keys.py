from __future__ import print_function

from collections import defaultdict
from itertools import chain

from tabulate import tabulate

from commcare_cloud.commands.command_base import CommandBase
from commcare_cloud.environment.main import get_environment
from commcare_cloud.environment.paths import get_available_envs


class ListVaultKeys(CommandBase):
    command = 'list-vault-keys'
    help = """
    Audit the structure of vault.yml files.

    A password will be required for each encrypted vault file in the env.
    
    For each vault key a value will be printed for each environments:
      * '' (blank)  : indicates that the key does not exist for this environment or is empty
      * 'x'         : indicates that the value exists and is unique among the environments that were analysed
      * 'enva,envb' : indicates that this value is shared with the listed environments
    """

    def run(self, args, unknown_args):
        envs = sorted(get_available_envs(exclude_symlinks=True))
        var_keys = {}
        for env in envs:
            print('[{} (blank to skip)] '.format(env), end='')
            environment = get_environment(env)
            passwd = environment.secrets_backend._get_ansible_vault_password()
            if passwd:
                var_keys[env] = dict(get_flat_list_of_keys(environment.secrets_backend._get_vault_variables_and_record()))

        headers = ["key"] + [env for env in envs if env in var_keys]

        rows = []
        for key in sorted(set(chain.from_iterable(var_keys.values()))):
            row = ['.'.join(part if part is not None else '*' for part in key)]
            by_var = defaultdict(set)
            for env in envs:
                value = var_keys.get(env, {}).get(key, None)
                if value:
                    by_var[value].add(env)

            for env in envs:
                if env not in var_keys:
                    continue
                if key in var_keys[env]:
                    duplicates = by_var[var_keys[env][key]] - set([env])
                    row.append(','.join(duplicates) if duplicates else 'x')
                else:
                    row.append('')
            rows.append(row)
        print(tabulate(rows, headers=headers, tablefmt='simple'))


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
        yield path, nested_config
