from __future__ import print_function
import argparse
import json
import os
import random
import string
import subprocess
import sys
import shutil
import uuid

import re

import jinja2
import yaml
import jsonobject

from commcare_cloud.environment.main import get_environment

TEMPLATE_DIR = os.path.join(os.path.dirname(__file__), 'environment')
j2 = jinja2.Environment(loader=jinja2.FileSystemLoader(TEMPLATE_DIR))


class StrictJsonObject(jsonobject.JsonObject):
    _allow_dynamic_properties = False


class Spec(StrictJsonObject):
    """
    Parser for spec files

    These files declare how many machines should be allocated for each role.
    See specs/example_spec.yml for an example.

    """
    aws_config = jsonobject.ObjectProperty(lambda: AwsConfig)
    settings = jsonobject.ObjectProperty(lambda: Settings)
    allocations = jsonobject.DictProperty(lambda: Allocation)

    @classmethod
    def wrap(cls, obj):
        allocations = {
            key: {'count': value} if isinstance(value, int) else value
            for key, value in obj.get('allocations', {}).items()
        }
        obj['allocations'] = allocations
        return super(Spec, cls).wrap(obj)


class AwsConfig(StrictJsonObject):
    pem = jsonobject.StringProperty()
    ami = jsonobject.StringProperty()
    type = jsonobject.StringProperty()
    key_name = jsonobject.StringProperty()
    security_group_id = jsonobject.StringProperty()
    subnet = jsonobject.StringProperty()
    data_volume = jsonobject.DictProperty(exclude_if_none=True)
    boot_volume = jsonobject.DictProperty(exclude_if_none=True)

    @classmethod
    def wrap(cls, data):
        if 'boot_volume' in data:
            assert data['boot_volume']['DeviceName'] == '/dev/sda1', (
                "AWS EC2 instances always use /dev/sda1 as the boot volume, "
                "so please set your spec's boot_volume.DeviceName to '/dev/sda1'."
            )
        return super(AwsConfig, cls).wrap(data)


class Settings(StrictJsonObject):
    users = jsonobject.StringProperty(default='dimagi')


class Allocation(StrictJsonObject):
    count = jsonobject.IntegerProperty(default=None)  # None means all here
    from_ = jsonobject.StringProperty(name='from')


class Inventory(StrictJsonObject):
    """
    This is an internal representation of the info we'll put in an ansible inventory file

    It's not structured the same way ansible inventory files are,
    because conceptually we treat host "groups" (just a way to name individual hosts)
    differently from "actual" groups (which we use to define roles).

    """
    all_hosts = jsonobject.ListProperty(lambda: Host)
    all_groups = jsonobject.DictProperty(lambda: Group)


class Host(StrictJsonObject):
    name = jsonobject.StringProperty()
    public_ip = jsonobject.StringProperty()
    private_ip = jsonobject.StringProperty()
    vars = jsonobject.DictProperty()


class Group(StrictJsonObject):
    name = jsonobject.StringProperty()
    host_names = jsonobject.ListProperty(unicode)
    vars = jsonobject.DictProperty()


def provision_machines(spec, env_name=None, create_machines=True):
    if env_name is None:
        env_name = u'hq-{}'.format(
            ''.join(random.choice(string.ascii_lowercase + string.digits) for _ in range(7))
        )
    environment = get_environment(env_name)
    inventory = bootstrap_inventory(spec, env_name)
    if create_machines:
        instance_ids = ask_aws_for_instances(env_name, spec.aws_config, len(inventory.all_hosts))
    else:
        instance_ids = None

    while True:
        instance_ip_addresses = poll_for_aws_state(env_name, instance_ids)
        if instance_ip_addresses:
            break

    hosts_by_name = {}

    for host, (public_ip, private_ip) in zip(inventory.all_hosts, instance_ip_addresses.values()):
        host.public_ip = public_ip
        host.private_ip = private_ip
        host.vars['hostname'] = host.name
        hosts_by_name[host.name] = host

    for i, host_name in enumerate(inventory.all_groups['kafka'].host_names):
        hosts_by_name[host_name].vars['kafka_broker_id'] = i
        hosts_by_name[host_name].vars['swap_size'] = '2G'

    for host_name in inventory.all_groups['elasticsearch'].host_names:
        hosts_by_name[host_name].vars['elasticsearch_node_name'] = host_name

    if spec.aws_config.data_volume:
        inventory.all_groups['lvm'] = Group(name='lvm')
        for group in inventory.all_groups:
            for host_name in inventory.all_groups[group].host_names:
                hosts_by_name[host_name].vars.update({
                    'datavol_device': '/dev/mapper/consolidated-data',
                    'devices': "'{}'".format(json.dumps([spec.aws_config.data_volume['DeviceName']])),
                    'partitions': "'{}'".format(json.dumps(['{}1'.format(spec.aws_config.data_volume['DeviceName'])])),
                })
                if host_name not in inventory.all_groups['lvm'].host_names:
                    inventory.all_groups['lvm'].host_names.append(host_name)

    save_inventory(environment, inventory)
    copy_default_vars(environment, spec.aws_config)
    save_app_processes_yml(environment, inventory)
    save_fab_settings_yml(environment)
    save_meta_yml(environment, env_name, spec.settings.users)


def alphanumeric_sort_key(key):
    """
    Sort the given iterable in the way that humans expect.
    Thanks to http://stackoverflow.com/a/2669120/240553
    """
    import re
    convert = lambda text: int(text) if text.isdigit() else text
    return [convert(c) for c in re.split('([0-9]+)', key)]


def bootstrap_inventory(spec, env_name):
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
                host_names = sorted(
                    inventory.all_groups[allocation.from_].host_names,
                    key=alphanumeric_sort_key,
                )[:allocation.count]  # if count is None, this is all machines
                inventory.all_groups[role] = Group(
                    name=role,
                    host_names=[host_name for host_name in host_names],
                    vars={},
                )
            else:
                new_host_names = set()
                for i in range(allocation.count):
                    host_name = '{env}-{group}-{i}'.format(env=env_name, group=role, i=i)
                    host_name = string.replace(host_name, '_', '-')
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


def ask_aws_for_instances(env_name, aws_config, count):
    cache_file = '{env}-aws-new-instances.json'.format(env=env_name)
    if os.path.exists(cache_file):
        cache_file_response = raw_input("\n{} already exists. Enter: "
                                        "\n(d) to delete the file AND environment directory containing it, and"
                                        " terminate the existing aws instances or "
                                        "\n(anything) to continue using this file and these instances."
                                        "\n Enter selection: ".format(cache_file))
        if cache_file_response == 'd':
            # Remove old cache file and terminate existing instances for this env
            print("Terminating existing instances for {}".format(env_name))
            subprocess.call(['commcare-cloud-bootstrap', 'terminate',  env_name])
            print("Deleting file: {}".format(cache_file))
            os.remove(cache_file)
            env_dir = get_environment(env_name).paths.get_env_file_path('')
            if os.path.isdir(env_dir):
                print("Deleting environment dir: {}".format(env_name))
                shutil.rmtree(env_dir)

    if not os.path.exists(cache_file):
        # Provision new instances for this env
        print("Provisioning new instances.")
        cmd_parts = [
            'aws', 'ec2', 'run-instances',
            '--image-id', aws_config.ami,
            '--count', unicode(int(count)),
            '--instance-type', aws_config.type,
            '--key-name', aws_config.key_name,
            '--security-group-ids', aws_config.security_group_id,
            '--subnet-id', aws_config.subnet,
            '--tag-specifications', 'ResourceType=instance,Tags=[{Key=env,Value=' + env_name + '}]',
        ]
        block_device_mappings = []
        if aws_config.boot_volume:
            block_device_mappings.append(aws_config.boot_volume)
        if aws_config.data_volume:
            block_device_mappings.append(aws_config.data_volume)
        cmd_parts.extend(['--block-device-mappings', json.dumps(block_device_mappings)])
        aws_response = subprocess.check_output(cmd_parts)
        with open(cache_file, 'w') as f:
            f.write(aws_response)
    else:
        # Use the existing instances
        with open(cache_file, 'r') as f:
            aws_response = f.read()
    aws_response = json.loads(aws_response)
    return {instance['InstanceId'] for instance in aws_response["Instances"]}


def print_describe_instances(describe_instances):
    for instance in get_instances(describe_instances):
        print("{InstanceId}\t{InstanceType}\t{ImageId}\t{State[Name]}\t{PublicIpAddress}\t{PrivateIpAddress}".format(**instance),
              file=sys.stderr)


def get_instances(describe_instances):
    for reservation in describe_instances['Reservations']:
        for instance in reservation['Instances']:
            yield instance


def raw_describe_instances(env_name):
    cmd_parts = [
        'aws', 'ec2', 'describe-instances', '--filters',
        'Name=instance-state-code,Values=16',
        'Name=tag:env,Values=' + env_name
    ]
    return json.loads(subprocess.check_output(cmd_parts))


def get_hosts_from_describe_instances(describe_instances):
    hosts = []
    for reservation in describe_instances['Reservations']:
        for instance in reservation['Instances']:
            hosts.append(
                Host(public_ip=instance['PublicIpAddress'],
                     private_ip=instance['PrivateIpAddress']))
    return hosts


def terminate_instances(instance_ids):
    cmd_parts = [
        'aws', 'ec2', 'terminate-instances', '--instance-ids',
    ] + instance_ids
    return json.loads(subprocess.check_output(cmd_parts))


def stop_instances(instance_ids):
    cmd_parts = [
        'aws', 'ec2', 'stop-instances', '--instance-ids',
    ] + instance_ids
    return json.loads(subprocess.check_output(cmd_parts))


def get_inventory_from_file(environment):
    """Parse inventory file created from ``inventory.ini.j2``.

    This is not a general inventory parser and only handles a subset
    of inventory features."""
    inventory = Inventory()
    state = None
    with open(environment.paths.inventory_ini) as f:
        for line in f.readlines():
            group_line_match = re.match(r'^\[\s*(.*)\s*\]\s*$', line)
            if re.match(r'^\s*$', line):
                continue
            if group_line_match:
                section_name = group_line_match.groups()[0]
                if section_name.endswith(':children'):
                    state = 'parsing-group'
                    current_group_name = section_name[:-len(':children')]
                    current_group = Group(name=current_group_name)
                    inventory.all_groups[current_group_name] = current_group
                else:
                    state = 'parsing-host'
                    current_host_name = section_name
            else:
                if state == 'parsing-host':
                    line_groups = list(re.split(r'\s+', line.strip()))
                    private_ip, variables = line_groups[0], line_groups[1:]
                    variables = dict(var.strip().split('=') for var in variables)
                    public_ip = variables.pop('ansible_host')
                    host = Host(name=current_host_name, private_ip=private_ip, public_ip=public_ip,
                                vars=variables)
                    inventory.all_hosts.append(host)
                elif state == 'parsing-group':
                    host_name = line.strip()
                    current_group.host_names.append(host_name)
                else:
                    raise ValueError('Encountered items outside a section')
    return inventory


def update_inventory_public_ips(inventory, new_hosts):
    assert len(inventory.all_hosts) == len(new_hosts)
    assert {host.private_ip for host in inventory.all_hosts} == {host.private_ip for host in new_hosts}
    new_host_by_private_ip = {host.private_ip: host for host in new_hosts}
    for host in inventory.all_hosts:
        host.public_ip = new_host_by_private_ip[host.private_ip].public_ip


def poll_for_aws_state(env_name, instance_ids=None):
    describe_instances = raw_describe_instances(env_name)
    print_describe_instances(describe_instances)

    instances = [instance
                 for reservation in describe_instances['Reservations']
                 for instance in reservation['Instances']]
    if instance_ids is not None:
        unfinished_instances = instance_ids - {
            instance['InstanceId'] for instance in instances
            if instance.get('PublicIpAddress') and instance.get('PublicDnsName')
        }
    else:
        unfinished_instances = ()

    if not unfinished_instances:
        return {
            instance['InstanceId']: (instance['PublicIpAddress'], instance['PrivateIpAddress'])
            for instance in instances
            if instance_ids is None or instance['InstanceId'] in instance_ids
        }


def save_inventory(environment, inventory):
    template = j2.get_template('inventory.ini.j2')
    inventory_file_contents = template.render(inventory=inventory)
    inventory_file = environment.paths.inventory_ini
    if not os.path.exists(os.path.dirname(inventory_file)):
        os.makedirs(os.path.dirname(inventory_file))
    with open(inventory_file, 'w') as f:
        f.write(inventory_file_contents)
    print('inventory file saved to {}'.format(inventory_file),
          file=sys.stderr)


def save_vault_yml(environment):
    def generate_uuid():
        return str(uuid.uuid4())
    j2.globals.update(generate_uuid=generate_uuid)
    template = j2.get_template('private.yml.j2')
    vault_file_contents = template.render(deploy_env=environment.name)
    vault_file = environment.paths.vault_yml
    with open(vault_file, 'w') as f:
        f.write(vault_file_contents)
    print('vault file saved to {}'.format(vault_file),
          file=sys.stderr)

def save_app_processes_yml(environment, inventory):
    template = j2.get_template('app-processes.yml.j2')
    celery_host_name = inventory.all_groups['celery'].host_names[0]
    pillowtop_host_name = inventory.all_groups['pillowtop'].host_names[0]
    celery_host, = [host for host in inventory.all_hosts if host.name == celery_host_name]
    pillowtop_host, = [host for host in inventory.all_hosts if host.name == pillowtop_host_name]
    contents = template.render(celery_host=celery_host, pillowtop_host=pillowtop_host)
    with open(environment.paths.app_processes_yml, 'w') as f:
        f.write(contents)


def save_meta_yml(environment, env_name, users):
    template = j2.get_template('meta.yml.j2')
    contents = template.render(env_name=env_name, users=users)
    with open(environment.paths.meta_yml, 'w') as f:
        f.write(contents)


def save_fab_settings_yml(environment):
    with open(environment.paths.fab_settings_yml, 'w') as f:
        f.write('')


def copy_default_vars(environment, aws_config):
    save_vault_yml(environment)

    vars_public = environment.paths.public_yml
    vars_postgresql = environment.paths.postgresql_yml
    vars_proxy = environment.paths.proxy_yml
    if os.path.exists(TEMPLATE_DIR) and not os.path.exists(vars_public):
        shutil.copyfile(os.path.join(TEMPLATE_DIR, 'public.yml'), vars_public)
        shutil.copyfile(os.path.join(TEMPLATE_DIR, 'postgresql.yml'), vars_postgresql)
        shutil.copyfile(os.path.join(TEMPLATE_DIR, 'proxy.yml'), vars_proxy)
        with open(vars_public, 'a+') as f:
            if os.path.isfile(os.path.expanduser(aws_config.pem)):
                f.write('commcare_cloud_pem: {pem}\n'.format(pem=aws_config.pem))
            else:
                print("The pem file {} specified in {} does not exist. Exiting.".format(
                    aws_config.pem, os.path.join(TEMPLATE_DIR, 'public.yml')))
                sys.exit(1)


class Provision(object):
    command = 'provision'
    help = """Provision a new environment based on a spec yaml file. (See example_spec.yml.)"""

    @staticmethod
    def make_parser(parser):
        parser.add_argument('spec')
        parser.add_argument('--env')
        parser.add_argument('--skip-create', dest='create_machines', action='store_false',
                            default=True)

    @staticmethod
    def run(args):
        with open(args.spec) as f:
            spec = yaml.load(f)

        spec = Spec.wrap(spec)
        provision_machines(spec, args.env, create_machines=args.create_machines)


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


class Terminate(object):
    command = 'terminate'
    help = """Terminate instances for a given env"""

    @staticmethod
    def make_parser(parser):
        parser.add_argument('env')

    @staticmethod
    def run(args):
        describe_instances = raw_describe_instances(args.env)
        instance_ids = [instance['InstanceId'] for instance in get_instances(describe_instances)]
        if instance_ids:
            terminate_instances_result = terminate_instances(instance_ids)
            print(terminate_instances_result)
            print(instance_ids)
        else:
            print("No instances found to terminate.")


class Stop(object):
    command = 'stop'
    help = """Stop instances for a given env"""

    @staticmethod
    def make_parser(parser):
        parser.add_argument('env')

    @staticmethod
    def run(args):
        describe_instances = raw_describe_instances(args.env)
        instance_ids = [instance['InstanceId'] for instance in get_instances(describe_instances)]
        if instance_ids:
            stop_instances_result = stop_instances(instance_ids)
            print(stop_instances_result)
            print(instance_ids)
        else:
            print("No instances found to stop.")


class Reip(object):
    command = 'reip'
    help = ("Rewrite the public IP addresses in the inventory for an env. "
            "Useful after reboot.")

    @staticmethod
    def make_parser(parser):
        parser.add_argument('env')

    @staticmethod
    def run(args):
        describe_instances = raw_describe_instances(args.env)
        environment = get_environment(args.env)
        new_hosts = get_hosts_from_describe_instances(describe_instances)
        inventory = get_inventory_from_file(environment)
        update_inventory_public_ips(inventory, new_hosts)
        save_inventory(environment, inventory)


STANDARD_ARGS = [
    Provision,
    Show,
    Reip,
    Terminate,
    Stop,
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
