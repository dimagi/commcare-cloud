from __future__ import print_function
import json
import sys
import tempfile
from copy import deepcopy

import boto3
import jsonobject
import os
import re
import runpy
import subprocess
from collections import namedtuple, deque

from botocore.exceptions import ClientError
from memoized import memoized_property

from commcare_cloud.alias import commcare_cloud
from commcare_cloud.cli_utils import ask, print_command
from commcare_cloud.commands.command_base import CommandBase, CommandError
from commcare_cloud.commands.terraform.aws import aws_sign_in
from commcare_cloud.environment.main import get_environment


class TerraformMigrateState(CommandBase):
    command = 'terraform-migrate-state'
    help = """
    Apply unapplied state migrations in commcare_cloud/commands/terraform/migrations

    This migration tool should exist as a generic tool for terraform,
    but terraform is still not that mature, and it doesn't seem to exist yet.

    Terraform assigns each resource an address so that it can map it back to the code.
    However, often when you change the code, the addresses no longer map to the same place.
    For this, terraform offers the terraform state mv <address> <new_address> command,
    so you can tell it how existing resources map to your new code.

    This is a tedious task, and often follows a very predictable renaming pattern.
    This command helps fill this gap.
    """

    def run(self, args, unknown_args):
        environment = get_environment(args.env_name)
        remote_migration_state_manager = RemoteMigrationStateManager(environment.terraform_config)
        remote_migration_state = remote_migration_state_manager.fetch()
        migrations = get_migrations()

        applied_migrations = migrations[:remote_migration_state.number]
        unapplied_migrations = migrations[remote_migration_state.number:]

        # make sure remote checkpoint is consistent with migrations in code
        if applied_migrations:
            assert (applied_migrations[-1].number, applied_migrations[-1].slug) == \
                   (remote_migration_state.number, remote_migration_state.slug), \
                (remote_migration_state, applied_migrations[-1])
        else:
            assert (0, None) == (remote_migration_state.number, remote_migration_state.slug), \
                remote_migration_state

        if not unapplied_migrations:
            print("No migrations to apply")
            return
        state = terraform_list_state(args.env_name, unknown_args)
        print("Applying the following changes:{}".format(
            ''.join('\n  - {:0>4} {}'.format(migration.number, migration.slug)
                    for migration in unapplied_migrations)
        ))
        print("which will result in the following moves being made:")
        migration_plans = make_migration_plans(environment, state, unapplied_migrations, log=print)
        if ask("Do you want to apply this migration?"):
            apply_migration_plans(
                environment, migration_plans,
                remote_migration_state_manager=remote_migration_state_manager, log=print)


Migration = namedtuple('Migration', 'number slug get_new_resource_address')
MigrationPlan = namedtuple('MigrationPlan', 'migration start_state end_state moves')


class RemoteMigrationState(jsonobject.JsonObject):
    checkpoint = jsonobject.StringProperty()
    slug = jsonobject.StringProperty()


class RemoteMigrationStateManager(object):
    def __init__(self, terraform_config):
        self.aws_profile = terraform_config.aws_profile
        self.environment = terraform_config.environment
        self.state_bucket = terraform_config.state_bucket

    @property
    def s3_filename(self):
        return 'migration-state/{environment}.json'.format(environment=self.environment)

    @memoized_property
    def s3_client(self):

        return boto3.session.Session(profile_name=aws_sign_in(self.aws_profile)).client('s3')

    def fetch(self):
        """
        Fetch remote migration state from S3

        Essentially:

        AWS_PROFILE={aws_profile} aws s3 cp s3://{state_bucket}/migration-state/{environment}.json {tempfile}

        wrapped as as a RemoteMigrationState object.
        """

        temp_filename = tempfile.mktemp()
        try:

            try:
                self.s3_client.download_file(self.state_bucket, self.s3_filename, temp_filename)
            except ClientError as e:
                if 'Not Found' in e.message:
                    return RemoteMigrationState(number=0, slug=None)
                else:
                    print(e.message, file=sys.stderr)
                    error_code = e.response.get('Error', {}).get('Code', 'Unknown')
                    raise CommandError('Request to S3 exited with code {}'.format(error_code))
            else:
                with open(temp_filename) as f:
                    return RemoteMigrationState.wrap(json.load(f))

        finally:
            if os.path.exists(temp_filename):
                os.remove(temp_filename)

    def push(self, remote_migration_state):
        """
        Push RemoteMigrationState object to S3

        Essentially:
        AWS_PROFILE={aws_profile} aws s3 cp {tempfile} s3://{state_bucket}/migration-state/{environment}.json
        after dumping the object to tempfile
        """
        temp_filename = tempfile.mktemp()
        try:
            with open(temp_filename, 'w') as f:
                json.dump(remote_migration_state.to_json(), f)

            try:
                self.s3_client.upload_file(temp_filename, self.state_bucket, self.s3_filename)
            except ClientError as e:
                print(e.message, file=sys.stderr)
                error_code = e.response.get('Error', {}).get('Code', 'Unknown')
                raise CommandError('aws exited with code {} while updating remote state to {}'
                                   .format(error_code, remote_migration_state.to_json()))
        finally:
            if os.path.exists(temp_filename):
                os.remove(temp_filename)


def terraform_list_state(env_name, unknown_args):
    cmd_parts = ['commcare-cloud', env_name, 'terraform', 'state', 'list'] + unknown_args
    output = subprocess.check_output(cmd_parts)
    return output.strip().splitlines()


MIGRATIONS_ROOT = os.path.join(os.path.dirname(__file__), 'migrations')


def get_migrations():
    file_names = sorted(os.listdir(MIGRATIONS_ROOT))
    matcher = re.compile(r'^(\d\d\d\d)_(\w+)\.py')
    migrations = []
    for file_name in file_names:
        match = matcher.match(file_name)
        if match:
            number_string, slug = match.groups()
            number = int(number_string)
            if number == 0:
                continue
            get_new_resource_address = runpy.run_path(os.path.join(MIGRATIONS_ROOT, file_name)).get('get_new_resource_address')
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
        self._temp_counter = -1

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

    def temp_counter(self):
        self._temp_counter += 1
        return self._temp_counter

    def assign_temp_address(self, new_address):
        address_index_syntax_matcher = re.compile(r'(\[\d+\]$)')
        parts = address_index_syntax_matcher.split(new_address)
        temp_suffix = '-tmp-{}'.format(self.temp_counter())
        if parts[-1] == '':
            parts.insert(-2, temp_suffix)
        else:
            parts.append(temp_suffix)
        return ''.join(parts)


def make_migration_plan(environment, start_state, migration):
    state = _SimulatedState(start_state)

    theoretical_moves = [
        # A get_new_resource_address(address) of None means no move
        (state.get_resource(address), migration.get_new_resource_address(environment, address) or address)
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
            temp_address = state.assign_temp_address(new_address)
            moves.append(state.move(resource, temp_address))
            # put it back on the end of the queue
            # to be moved to the proper location once it frees up
            move_queue.append((resource, new_address))

    assert set(state.list()) == set(end_state), (sorted(state.list()), sorted(end_state))
    return MigrationPlan(migration=migration, start_state=start_state, end_state=end_state, moves=moves)


def make_migration_plans(environment, start_state, migrations, log=lambda x: None):
    intermediate_state = start_state
    migration_plans = []
    for migration in migrations:
        log('  [{:0>4} {}]'.format(migration.number, migration.slug))
        migration_plan = make_migration_plan(environment, intermediate_state, migration)
        intermediate_state = migration_plan.end_state
        for start_address, end_address in migration_plan.moves:
            log('    {} => {}'.format(start_address, end_address))
        migration_plans.append(migration_plan)
    return migration_plans


def apply_migration_plans(environment, migration_plans, remote_migration_state_manager,
                          log=lambda x: None):
    for migration_plan in migration_plans:
        migration = migration_plan.migration
        log('  [{:0>4} {}]'.format(migration.number, migration.slug))
        for start_address, end_address in migration_plan.moves:
            log('    {} => {}'.format(start_address, end_address))
            commcare_cloud(environment.paths.env_name, 'terraform', 'state', 'mv',
                           start_address, end_address)
        remote_migration_state_manager.push(
            RemoteMigrationState(number=migration.number, slug=migration.slug))
