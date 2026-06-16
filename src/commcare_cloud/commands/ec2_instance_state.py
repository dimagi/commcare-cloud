import json

from clint.textui import puts

from commcare_cloud.commands import shared_args
from commcare_cloud.commands.ansible.ansible_playbook import (
    run_ansible_playbook,
)
from commcare_cloud.commands.ansible.helpers import AnsibleContext
from commcare_cloud.commands.command_base import (
    Argument,
    CommandBase,
    CommandError,
)
from commcare_cloud.commands.terraform.aws import is_aws_env

ACTIONS = ['describe', 'start', 'stop', 'stop_and_start']


class Ec2InstanceState(CommandBase):
    command = 'ec2-instance-state'
    help = """
    Manage the EC2 instance state (start/stop/describe) of hosts in an AWS environment.

    `start` and `stop` show a check-mode preview of the state transitions
    and ask for confirmation before applying; `stop_and_start` asks for
    confirmation directly (a check-mode preview of a full cycle would show
    no net state change); `describe` just runs.

    Example:

    ```
    commcare-cloud <env> ec2-instance-state describe webworkers
    commcare-cloud <env> ec2-instance-state stop celery:pillowtop
    commcare-cloud <env> ec2-instance-state stop_and_start 10.201.11.133 10.201.11.134
    ```
    """

    run_setup_on_control_by_default = False

    arguments = (
        Argument('action', choices=ACTIONS, help="""
            What to do to the matched instances.
            `describe` reports their current state without changing anything;
            `start`/`stop` are idempotent;
            `stop_and_start` stops the instances (if running) and starts them again.
        """),
        Argument('inventory_group', nargs='+', help="""
            One or more inventory items to act on. Each can be a group
            (e.g. `webworkers`), an individual host name or private IP
            (e.g. `10.201.11.133`), or any ansible host pattern
            (e.g. `celery:pillowtop`).
        """),
        Argument('--no-wait', action='store_true', help="""
            Return as soon as the state change is issued instead of waiting
            for instances to reach their final state.
        """),
        shared_args.SKIP_CHECK_ARG,
        shared_args.QUIET_ARG,
    )

    def run(self, args, unknown_args):
        ansible_context = AnsibleContext(args)
        environment = ansible_context.environment
        if not is_aws_env(environment):
            raise CommandError(
                "ec2-instance-state can only be used in AWS environments "
                f"(no terraform config found for {environment.name!r})")

        instance_ids_by_host = get_instance_ids_by_host(environment, args.inventory_group)

        all_hosts = {host.name for host in environment.inventory_manager.get_hosts('all')
                     if not host.implicit}
        if set(instance_ids_by_host) >= all_hosts:
            raise CommandError(
                f"Refusing to run ec2-instance-state against all hosts in {environment.name!r}. "
                "Target a specific group, host, or pattern instead.")

        self.log("Matched hosts:")
        print(instance_ids_by_host)
        for host, instance_id in instance_ids_by_host.items():
            puts("  {} ({})".format(host, instance_id))

        extra_vars = {
            'ec2_instance_state_command': args.action,
            'ec2_instance_state_wait': not args.no_wait,
        }

        describe = args.action == 'describe'
        return run_ansible_playbook(
            'ec2_instance_state.yml',
            ansible_context,
            # describe is read-only; apply it directly without prompting
            skip_check=args.skip_check or describe,
            quiet=args.quiet or describe,
            # A check-mode stop_and_start predicts no net state change, so its
            # diff preview is empty and misleading; confirm directly instead.
            always_skip_check=args.action == 'stop_and_start',
            limit=','.join(instance_ids_by_host),
            unknown_args=['-e', json.dumps(extra_vars)] + list(unknown_args),
        )


def get_instance_ids_by_host(environment, inventory_items):
    """Resolve inventory items to {host name: ec2_instance_id}, in inventory order."""
    pattern = ','.join(inventory_items)
    # Exclude ansible's implicit localhost, which get_hosts returns for
    # 'localhost'/'127.0.0.1' patterns even when it is not in the inventory.
    hosts = [host for host in environment.inventory_manager.get_hosts(pattern)
             if not host.implicit]
    if not hosts:
        raise CommandError("No hosts in inventory match {!r}".format(pattern))

    instance_ids_by_host = {}
    for host in hosts:
        instance_id = host.vars.get('ec2_instance_id')
        if instance_id:
            instance_ids_by_host[host.name] = instance_id
    
    return instance_ids_by_host
