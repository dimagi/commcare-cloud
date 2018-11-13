import re
from collections import namedtuple

from nose.tools import assert_equal

from commcare_cloud.commands.terraform.terraform_migrate_state import get_migrations, \
    Migration, make_migration_plans, MigrationPlan


def test_numbering():
    """
    Test that terraform state migration files are numbered correctly

    starting at 1, with no gaps and no repeats
    """
    migrations = get_migrations()
    numbers = [migration.number for migration in migrations]
    if numbers:
        assert numbers == list(range(1, numbers[-1] + 1)), numbers


def test_make_migration_plans():
    state = [
        'module.commcarehq.module.servers.aws_instance.server[0]',
        'module.commcarehq.module.servers.aws_instance.server[1]',
        'module.commcarehq.module.servers.aws_instance.server[2]',
        'module.commcarehq.module.servers.aws_instance.server[3]',
        'module.commcarehq.module.servers.aws_instance.server[4]',
        'module.commcarehq.module.Users.aws_iam_account_alias.alias',
        'aws_key_pair.droberts',
    ]
    server_names = ['web0', 'celery0', 'proxy0', 'couch0', 'es0']

    def change_root(environment, old_resource_address):
        parts = old_resource_address.split('.')
        if parts[:2] == ['module', 'commcarehq']:
            parts = parts[2:]
        return '.'.join(parts)

    def rotate_servers(environment, old_resource_address):
        parts = old_resource_address.split('.')
        address_index_syntax_matcher = re.compile(r'\[(\d+)\]$')
        if parts[:3] == ['module', 'servers', 'aws_instance'] and parts[3].startswith(
                'server'):
            index = int(address_index_syntax_matcher.search(parts[3]).group(1))
            if index == 2:
                index = 4
            elif index > 2:
                index -= 1
            parts = ['module', 'servers', 'aws_instance', 'server[{}]'.format(index)]
        return '.'.join(parts)

    def name_servers(environment, old_resource_address):
        parts = old_resource_address.split('.')
        address_index_syntax_matcher = re.compile(r'\[(\d+)\]$')
        if parts[:3] == ['module', 'servers', 'aws_instance'] and parts[3].startswith('server'):
            index = int(address_index_syntax_matcher.search(parts[3]).group(1))
            name = server_names[index]
            parts = ['aws_instance', name]
        return '.'.join(parts)

    migration = [
        Migration(number=1, slug='change-root', get_new_resource_address=change_root),
        Migration(number=2, slug='rotate-servers', get_new_resource_address=rotate_servers),
        Migration(number=3, slug='name-servers', get_new_resource_address=name_servers),
    ]
    environment = namedtuple('MockEnv', 'env_name')(env_name='test')
    migration_plans = make_migration_plans(environment, state, migration)

    expected_state_0 = [
        'module.commcarehq.module.servers.aws_instance.server[0]',
        'module.commcarehq.module.servers.aws_instance.server[1]',
        'module.commcarehq.module.servers.aws_instance.server[2]',
        'module.commcarehq.module.servers.aws_instance.server[3]',
        'module.commcarehq.module.servers.aws_instance.server[4]',
        'module.commcarehq.module.Users.aws_iam_account_alias.alias',
        'aws_key_pair.droberts',
    ]
    expected_moves_0 = [
        ['module.commcarehq.module.servers.aws_instance.server[0]', 'module.servers.aws_instance.server[0]'],
        ['module.commcarehq.module.servers.aws_instance.server[1]', 'module.servers.aws_instance.server[1]'],
        ['module.commcarehq.module.servers.aws_instance.server[2]', 'module.servers.aws_instance.server[2]'],
        ['module.commcarehq.module.servers.aws_instance.server[3]', 'module.servers.aws_instance.server[3]'],
        ['module.commcarehq.module.servers.aws_instance.server[4]', 'module.servers.aws_instance.server[4]'],
        ['module.commcarehq.module.Users.aws_iam_account_alias.alias', 'module.Users.aws_iam_account_alias.alias'],
    ]
    expected_state_1 = [
        'module.servers.aws_instance.server[0]',
        'module.servers.aws_instance.server[1]',
        'module.servers.aws_instance.server[2]',
        'module.servers.aws_instance.server[3]',
        'module.servers.aws_instance.server[4]',
        'module.Users.aws_iam_account_alias.alias',
        'aws_key_pair.droberts',
    ]
    expected_moves_1 = [
        ['module.servers.aws_instance.server[2]', 'module.servers.aws_instance.server-tmp-0[4]'],
        ['module.servers.aws_instance.server[3]', 'module.servers.aws_instance.server[2]'],
        ['module.servers.aws_instance.server[4]', 'module.servers.aws_instance.server[3]'],
        ['module.servers.aws_instance.server-tmp-0[4]', 'module.servers.aws_instance.server[4]'],
    ]
    expected_state_2 = [
        'module.servers.aws_instance.server[0]',
        'module.servers.aws_instance.server[1]',
        'module.servers.aws_instance.server[4]',
        'module.servers.aws_instance.server[2]',
        'module.servers.aws_instance.server[3]',
        'module.Users.aws_iam_account_alias.alias',
        'aws_key_pair.droberts',
    ]
    expected_moves_2 = [
        ['module.servers.aws_instance.server[0]', 'aws_instance.web0'],
        ['module.servers.aws_instance.server[1]', 'aws_instance.celery0'],
        ['module.servers.aws_instance.server[4]', 'aws_instance.es0'],
        ['module.servers.aws_instance.server[2]', 'aws_instance.proxy0'],
        ['module.servers.aws_instance.server[3]', 'aws_instance.couch0'],
    ]
    expected_state_3 = [
        'aws_instance.web0',
        'aws_instance.celery0',
        'aws_instance.es0',
        'aws_instance.proxy0',
        'aws_instance.couch0',
        'module.Users.aws_iam_account_alias.alias',
        'aws_key_pair.droberts',
    ]
    assert_equal(len(migration_plans), 3)
    assert_equal(migration_plans[0], MigrationPlan(
        migration=migration[0],
        start_state=expected_state_0,
        moves=expected_moves_0,
        end_state=expected_state_1,
    ))
    assert_equal(migration_plans[1], MigrationPlan(
        migration=migration[1],
        start_state=expected_state_1,
        moves=expected_moves_1,
        end_state=expected_state_2,
    ))
    assert_equal(migration_plans[2], MigrationPlan(
        migration=migration[2],
        start_state=expected_state_2,
        moves=expected_moves_2,
        end_state=expected_state_3,
    ))
