from __future__ import print_function
import argparse
import json
import os
import random
import string
import subprocess
import sys
import shutil
from collections import namedtuple

import jinja2
import yaml
import jsonobject
from commcare_cloud.environment import get_inventory_filepath, \
    get_public_vars_filepath, get_vault_vars_filepath, ENVIRONMENTS_DIR, REPO_BASE

VARS_DIR = os.path.join(REPO_BASE, 'ansible', 'vars')


class Spec(jsonobject.JsonObject):
    aws_config = jsonobject.ObjectProperty(lambda: AwsConfig)
    allocations = jsonobject.DictProperty(lambda: Allocation)

    @classmethod
    def wrap(cls, obj):
        allocations = {
            key: {'count': value} if isinstance(value, int) else value
            for key, value in obj.get('allocations', {}).items()
        }
        obj['allocations'] = allocations
        return super(Spec, cls).wrap(obj)


class AwsConfig(jsonobject.JsonObject):
    pem = jsonobject.StringProperty()
    ami = jsonobject.StringProperty()
    type = jsonobject.StringProperty()
    key_name = jsonobject.StringProperty()
    security_group_id = jsonobject.StringProperty()
    subnet = jsonobject.StringProperty()


class Allocation(jsonobject.JsonObject):
    count = jsonobject.IntegerProperty()
    from_ = jsonobject.StringProperty(name='from')


class AnsibleInventory(jsonobject.JsonObject):
    all = jsonobject.ObjectProperty(lambda: AnsibleInventoryGroup)


class AnsibleInventoryGroup(jsonobject.JsonObject):
    children = jsonobject.DictProperty(lambda: AnsibleInventoryGroup, required=False)
    # values can be var:value dicts, but are often null
    hosts = jsonobject.DictProperty(jsonobject.DictProperty(), exclude_if_none=True)


class Host(jsonobject.JsonObject):
    name = jsonobject.StringProperty()
    public_ip = jsonobject.StringProperty()
    private_ip = jsonobject.StringProperty()
    vars = jsonobject.DictProperty()


class Group(jsonobject.JsonObject):
    name = jsonobject.StringProperty()
    host_names = jsonobject.ListProperty(unicode)
    vars = jsonobject.DictProperty()


class Inventory(jsonobject.JsonObject):
    all_hosts = jsonobject.ListProperty(Host)
    all_groups = jsonobject.DictProperty(Group)


def provision_machines(spec, env=None):
    if env is None:
        env = u'hq-{}'.format(
            ''.join(random.choice(string.ascii_lowercase + string.digits) for _ in range(7))
        )
    inventory = bootstrap_inventory(spec, env)
    instance_ids = ask_aws_for_instances(env, spec.aws_config, len(inventory.all_hosts))

    while True:
        instance_ip_addresses = poll_for_aws_state(env, instance_ids)
        if instance_ip_addresses:
            break

    hosts_by_name = {}

    for host, (public_ip, private_ip) in zip(inventory.all_hosts, instance_ip_addresses.values()):
        host.public_ip = public_ip
        host.private_ip = private_ip
        hosts_by_name[host.name] = host

    for i, host_name in enumerate(inventory.all_groups['kafka'].host_names):
        hosts_by_name[host_name].vars['kafka_broker_id'] = i
        hosts_by_name[host_name].vars['swap_size'] = '2G'

    for host_name in inventory.all_groups['elasticsearch'].host_names:
        hosts_by_name[host_name].vars['elasticsearch_node_name'] = host_name

    save_inventory(env, inventory)
    copy_default_vars(env, spec.aws_config)


def alphanumeric_sort_key(key):
    """
    Sort the given iterable in the way that humans expect.
    Thanks to http://stackoverflow.com/a/2669120/240553
    """
    import re
    convert = lambda text: int(text) if text.isdigit() else text
    return [convert(c) for c in re.split('([0-9]+)', key)]


def bootstrap_inventory(spec, env):
    incomplete = dict(spec.allocations.items())

    inventory = Inventory()

    while incomplete:
        for role, allocation in incomplete.items():
            if allocation.from_:
                if allocation.from_ not in spec.allocations:
                    raise KeyError('You specified an unknown group in the from field of {}: {}'
                                   .format(role, allocation.from_))
                if allocation.from_ in incomplete:
                    continue
                # This is kind of hacky because it does a string sort
                # on strings containing integers.
                # Once we have more than 10 it'll start sorting wrong
                host_names = sorted(
                    inventory.all_groups[allocation.from_].hosts,
                    key=alphanumeric_sort_key,
                )[:allocation.count]
                inventory.all_groups[role] = Group(
                    name=role,
                    host_names=[host_name for host_name in host_names],
                    vars={},
                )
            else:
                new_host_names = set()
                for i in range(allocation.count):
                    host_name = '{env}-{group}-{i}'.format(env=env, group=role, i=i)
                    new_host_names.add(host_name)
                    inventory.all_hosts.append(
                        Host(name=host_name, public_ip=None, private_ip=None, vars={}))
                inventory.all_groups[role] = Group(
                    name=role,
                    host_names=[host_name for host_name in new_host_names],
                    vars={},
                )

            del incomplete[role]
    return inventory


def ask_aws_for_instances(env, aws_config, count):
    cache_file = '{env}-aws-new-instances.json'.format(env=env)
    if os.path.exists(cache_file):
        with open(cache_file, 'r') as f:
            aws_response = f.read()
    else:
        cmd_parts = [
            'aws', 'ec2', 'run-instances',
            '--image-id', aws_config.ami,
            '--count', unicode(int(count)),
            '--instance-type', aws_config.type,
            '--key-name', aws_config.key_name,
            '--security-group-ids', aws_config.security_group_id,
            '--subnet-id', aws_config.subnet,
            '--tag-specifications', 'ResourceType=instance,Tags=[{Key=env,Value=' + env + '}]',
        ]
        aws_response = subprocess.check_output(cmd_parts)
        with open(cache_file, 'w') as f:
            f.write(aws_response)
    aws_response = json.loads(aws_response)
    return {instance['InstanceId'] for instance in aws_response["Instances"]}


def print_describe_instances(describe_instances):
    for reservation in describe_instances['Reservations']:
        for instance in reservation['Instances']:
            print("{InstanceId}\t{InstanceType}\t{ImageId}\t{State[Name]}\t{PublicIpAddress}\t{PublicDnsName}".format(**instance),
                  file=sys.stderr)


def raw_describe_instances(env):
    cmd_parts = [
        'aws', 'ec2', 'describe-instances', '--filters',
        'Name=instance-state-code,Values=16',
        'Name=tag:env,Values=' + env
    ]
    return json.loads(subprocess.check_output(cmd_parts))


def poll_for_aws_state(env, instance_ids):
    describe_instances = raw_describe_instances(env)
    print_describe_instances(describe_instances)

    instances = [instance
                 for reservation in describe_instances['Reservations']
                 for instance in reservation['Instances']]
    unfinished_instances = instance_ids - {
        instance['InstanceId'] for instance in instances
        if instance.get('PublicIpAddress') and instance.get('PublicDnsName')
    }
    if not unfinished_instances:
        return {
            instance['InstanceId']: (instance['PublicIpAddress'], instance['PrivateIpAddress'])
            for instance in instances
            if instance['InstanceId'] in instance_ids
        }


def save_inventory(env, inventory):
    j2 = jinja2.Environment(loader=jinja2.FileSystemLoader(os.path.dirname(__file__)))
    template = j2.get_template('inventory.ini.j2')
    inventory_file_contents = template.render(inventory=inventory)
    inventory_file = get_inventory_filepath(env)
    if not os.path.exists(os.path.dirname(inventory_file)):
        os.makedirs(os.path.dirname(inventory_file))
    with open(inventory_file, 'w') as f:
        f.write(inventory_file_contents)
    print('inventory file saved to {}'.format(inventory_file),
          file=sys.stderr)


def copy_default_vars(env, aws_config):
    vars_dir = VARS_DIR
    template_dir = os.path.join(vars_dir, '.commcare-cloud-bootstrap')
    new_dir = ENVIRONMENTS_DIR
    vars_public = get_public_vars_filepath(env)
    vars_vault = get_vault_vars_filepath(env)
    if os.path.exists(template_dir) and not os.path.exists(vars_public):
        shutil.copyfile(os.path.join(template_dir, 'private.yml'), vars_vault)
        shutil.copyfile(os.path.join(template_dir, 'public.yml'), vars_public)
        with open(vars_public, 'a') as f:
            f.write('commcare_cloud_root_user: ubuntu\n')
            f.write('commcare_cloud_pem: {pem}\n'.format(pem=aws_config.pem))
            f.write('commcare_cloud_strict_host_key_checking: no\n')
            f.write('commcare_cloud_use_vault: no\n')
        print('template vars dir copied to {}'.format(new_dir),
              file=sys.stderr)


class Provision(object):
    command = 'provision'
    help = """Provision a new environment based on a spec yaml file. (See example_spec.yml.)"""

    @staticmethod
    def make_parser(parser):
        parser.add_argument('spec')
        parser.add_argument('--env')

    @staticmethod
    def run(args):
        with open(args.spec) as f:
            spec = yaml.load(f)

        spec = Spec.wrap(spec)
        provision_machines(spec, args.env)


class Show(object):
    command = 'show'
    help = """Show provisioned instances for a given env"""

    @staticmethod
    def make_parser(parser):
        parser.add_argument('env')

    @staticmethod
    def run(args):
        describe_instances = raw_describe_instances(args.env)
        print_describe_instances(describe_instances)


STANDARD_ARGS = [
    Provision,
    Show,
]


def main():
    parser = argparse.ArgumentParser()
    subparsers = parser.add_subparsers(dest='command')

    for standard_arg in STANDARD_ARGS:
        standard_arg.make_parser(subparsers.add_parser(standard_arg.command, help=standard_arg.help))

    args = parser.parse_args()

    for standard_arg in STANDARD_ARGS:
        if args.command == standard_arg.command:
            standard_arg.run(args)
