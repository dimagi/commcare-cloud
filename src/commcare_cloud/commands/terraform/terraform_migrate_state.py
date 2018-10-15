import os
import random
import re
import runpy
import subprocess
from collections import namedtuple, deque

from commcare_cloud.commands.command_base import CommandBase


class TerraformMigrateState(CommandBase):
    command = 'terraform-migrate-state'
    help = "Apply unapplied state migrations in commcare_cloud/commands/terraform/migrations"

    def run(self, args, unknown_args):
        migrations = get_migrations(os.path.join(os.path.dirname(__file__), 'migrations'))
        # todo: apply only unapplied migrations!
        unapplied_migrations = migrations
        state = terraform_list_state(args.env_name, unknown_args)
        intermediate_state = state
        print("Applying the following changes:{}".format(
            ''.join('\n  - {:0>4} {}'.format(migration.number, migration.slug)
                    for migration in unapplied_migrations)
        ))
        print("which will result in the following moves being made:")
        for migration in unapplied_migrations:
            print('  [{:0>4} {}]'.format(migration.number, migration.slug))
            migration_plan = make_migration_plan(intermediate_state, migration)
            intermediate_state = migration_plan.end_state
            for start_address, end_address in migration_plan.moves:
                print('    {} => {}'.format(start_address, end_address))


Migration = namedtuple('Migration', 'number slug get_new_resource_address')
MigrationPlan = namedtuple('MigrationPlan', 'start_state end_state moves')


def terraform_list_state(env_name, unknown_args):
    cmd_parts = ['commcare-cloud', env_name, 'terraform', 'state', 'list'] + unknown_args
    output = subprocess.check_output(cmd_parts)
    return output.strip().splitlines()


def get_migrations(migrations_root):
    file_names = sorted(os.listdir(migrations_root))
    matcher = re.compile(r'^(\d\d\d\d)_(\w+)\.py')
    migrations = []
    for file_name in file_names:
        match = matcher.match(file_name)
        if match:
            number_string, slug = match.groups()
            number = int(number_string)
            if number == 0:
                continue
            get_new_resource_address = runpy.run_path(os.path.join(migrations_root, file_name)).get('get_new_resource_address')
            migrations.append(
                Migration(number=number, slug=slug,
                          get_new_resource_address=get_new_resource_address))
    return migrations


class _Resource(object):
    def __init__(self, original_address):
        self.original_address = original_address


class _SimulatedState(object):
    def __init__(self, addresses):
        self._address_to_resource = {address: _Resource('address') for address in addresses}
        self._resource_to_address = {
            resource: address for address, resource in self._address_to_resource.items()
        }

    def get_address(self, resource):
        return self._resource_to_address[resource]

    def get_resource(self, address):
        return self._address_to_resource[address]

    def list(self):
        return self._address_to_resource.keys()

    def address_is_free(self, address):
        return address not in self._address_to_resource

    def move(self, resource, new_address):
        if not self.address_is_free(new_address):
            raise Exception("Address already in use: {}".format(new_address))
        old_address = self._resource_to_address[resource]
        self._address_to_resource[new_address] = resource
        del self._address_to_resource[old_address]
        self._resource_to_address[resource] = new_address
        return [old_address, new_address]


def assign_temp_address(new_address, python_id):
    address_index_syntax_matcher = re.compile(r'(\[\d+\]$)')
    parts = address_index_syntax_matcher.split(new_address)
    temp_suffix = '-tmp-{}'.format(python_id)
    if parts[-1] == '':
        parts.insert(-3, temp_suffix)
    else:
        parts.append(temp_suffix)
    return ''.join(parts)


def make_migration_plan(start_state, migration):
    state = _SimulatedState(start_state)

    theoretical_moves = [
        # A get_new_resource_address(address) of None means no move
        (state.get_resource(address), migration.get_new_resource_address(address) or address)
        for address in start_state
    ]

    # This is just for an assertion at the end
    end_state = [end_address for _, end_address in theoretical_moves]
    move_queue = deque(theoretical_moves)

    moves = []

    while move_queue:
        resource, new_address = move_queue.popleft()
        if state.get_address(resource) == new_address:
            continue
        elif state.address_is_free(new_address):
            moves.append(state.move(resource, new_address))
        else:
            temp_address = assign_temp_address(new_address, id(resource))
            moves.append(state.move(resource, temp_address))
            # put it back on the end of the queue
            # to be moved to the proper location once it frees up
            move_queue.append((resource, new_address))

    assert set(state.list()) == set(end_state), (sorted(state.list()), sorted(end_state))
    return MigrationPlan(start_state=start_state, end_state=end_state, moves=moves)
