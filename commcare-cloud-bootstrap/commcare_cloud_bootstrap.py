from __future__ import print_function
import argparse
import json
import os
import random
import string
import subprocess
import sys
import shutil
import yaml
import jsonobject
from commcare_cloud.commcare_cloud import get_inventory_filepath, \
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


def provision_machines(spec, env=None):
    if env is None:
        env = u'hq-{}'.format(
            ''.join(random.choice(string.ascii_lowercase + string.digits) for i in range(7))
        )
    all_hosts, inventory = bootstrap_inventory(spec, env)
    instance_ids = ask_aws_for_instances(env, spec.aws_config, len(all_hosts))

    while True:
        instance_ip_addresses = poll_for_aws_state(env, instance_ids)
        if instance_ip_addresses:
            break

    ip_addresses_by_host = dict(zip(all_hosts, instance_ip_addresses.values()))

    for group_name, group in inventory.all.children.items():
        for host_name, host_vars in group.hosts.items():
            host_vars['ansible_host'] = str(ip_addresses_by_host[host_name])

    save_inventory(env, inventory)
    copy_default_vars(env, spec.aws_config)


def bootstrap_inventory(spec, env):
    inventory = AnsibleInventory()
    incomplete = dict(spec.allocations.items())

    all_hosts = set()

    while incomplete:
        for name, allocation in incomplete.items():
            if allocation.from_:
                if allocation.from_ not in spec.allocations:
                    raise KeyError('You specified an unknown group in the from field of {}: {}'
                                   .format(name, allocation.from_))
                if allocation.from_ in incomplete:
                    continue
                inventory.all.children[name] = AnsibleInventoryGroup(hosts={
                    host: {}
                    for host in inventory.all.children[allocation.from_].hosts.keys()[:allocation.count]
                })
            else:
                new_hosts = {
                    '{env}-{group}-{i}'.format(env=env, group=name, i=i)
                    for i in range(allocation.count)
                }
                inventory.all.children[name] = AnsibleInventoryGroup(hosts={
                    host: {} for host in new_hosts
                })
                all_hosts.update(new_hosts)
            del incomplete[name]
    return all_hosts, inventory


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

    aws_response = json.loads(aws_response)
    return {instance['InstanceId'] for instance in aws_response["Instances"]}


def print_describe_instances(describe_instances):
    for reservation in describe_instances['Reservations']:
        for instance in reservation['Instances']:
            print("{InstanceId}\t{InstanceType}\t{ImageId}\t{State[Name]}\t{PublicIpAddress}\t{PublicDnsName}".format(**instance),
                  file=sys.stderr)


def poll_for_aws_state(env, instance_ids):
    cmd_parts = [
        'aws', 'ec2', 'describe-instances', '--filters',
        'Name=instance-state-code,Values=16',
        'Name=tag:env,Values=' + env
    ]
    describe_instances = json.loads(subprocess.check_output(cmd_parts))
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
            instance['InstanceId']: instance['PublicIpAddress']
            for instance in instances
            if instance['InstanceId'] in instance_ids
        }


def save_inventory(env, inventory):
    inventory_file_contents = yaml.safe_dump(inventory.to_json(), default_flow_style=False)
    inventory_file = get_inventory_filepath(env)
    with open(inventory_file, 'w') as f:
        f.write(inventory_file_contents)
    print('inventory file saved to {}'.format(inventory_file),
          file=sys.stderr)


def copy_default_vars(env, aws_config):
    template_dir = os.path.join(VARS_DIR, 'dev')
    new_dir = ENVIRONMENTS_DIR
    if os.path.exists(VARS_DIR) and os.path.exists(template_dir) and not os.path.exists(new_dir):
        os.makedirs(new_dir)
        vars_public = get_public_vars_filepath(env)
        vars_vault = get_vault_vars_filepath(env)
        shutil.copyfile(os.path.join(template_dir, 'dev_private.yml'), vars_vault)
        shutil.copyfile(os.path.join(template_dir, 'dev_public.yml'),
                        vars_public)
        with open(vars_public, 'a') as f:
            f.write('commcare_cloud_root_user: ubuntu\n')
            f.write('commcare_cloud_pem: {pem}\n'.format(pem=aws_config.pem))
            f.write('commcare_cloud_strict_host_key_checking: no\n')
            f.write('commcare_cloud_use_vault: no\n')
        print('template vars dir copied to {}'.format(new_dir),
              file=sys.stderr)


def main():
    parser = argparse.ArgumentParser()
    parser.add_argument('spec')
    parser.add_argument('--env')

    args = parser.parse_args()

    with open(args.spec) as f:
        spec = yaml.load(f)
    spec = Spec.wrap(spec)
    provision_machines(spec, args.env)
