# coding: utf-8
import inspect
import os
import time
from datetime import datetime

import datadog
import yaml
from clint.textui import puts, colored, indent
from memoized import memoized

from commcare_cloud.cli_utils import ask, ask_option
from commcare_cloud.commands.ansible.helpers import AnsibleContext
from commcare_cloud.commands.ansible.run_module import run_ansible_module
from commcare_cloud.commands.command_base import CommandBase, Argument
from commcare_cloud.environment.main import get_environment

HQ_PROCESSES_SCOPE = 'webworkers,celery,pillowtop,formplayer,proxy'


class Downtime(CommandBase):
    command = 'downtime'
    help = """
    Manage downtime for the selected environment.

    This notifies Datadog of the planned downtime so that is is recorded
    in the history, and so that during it service alerts are silenced.
    """
    arguments = (
        Argument('action', choices=('start', 'end')),
        Argument('-m', '--message', help="""
            Optional message to set on Datadog.
        """),
    )

    def run(self, args, unknown_args):
        environment = get_environment(args.env_name)
        environment.create_generated_yml()
        ansible_context = AnsibleContext(args)

        if args.action == 'start':
            start_downtime(environment, ansible_context, args)

        if args.action == 'end':
            end_downtime(environment, ansible_context)


def end_downtime(environment, ansible_context):
    downtime = get_downtime_record(environment)
    if not downtime:
        puts(colored.yellow('Downtime record not found.'))
        end_downtime = ask("Do you want to continue?")
    else:
        end_downtime = ask("Do you want to start all CommCare services?")

    if end_downtime:
        supervisor_services(environment, ansible_context, 'start')
        if downtime:
            cancel_downtime_record(environment, downtime)


def start_downtime(environment, ansible_context, args):
    downtime = get_downtime_record(environment)
    if downtime:
        puts(colored.yellow('Downtime already active'))
        with indent():
            print_downtime(downtime)
        go_down = ask("Do you want to continue?")
    else:
        go_down = ask("Are you sure you want to stop all CommCare services?", strict=True)

    if go_down:
        if not downtime:
            create_downtime_record(environment, args.message)
        supervisor_services(environment, ansible_context, 'stop')
        wait_for_all_processes_to_stop(environment, ansible_context)


def wait_for_all_processes_to_stop(environment, ansible_context):
    while True:
        still_running = check_for_running_cchq_processes(environment, ansible_context)
        if not still_running:
            break

        options = ['abort', 'wait', 'continue', 'kill',]
        response = ask_option(inspect.cleandoc(
            """Some processes are still running. Do you want to:"
             - abort downtime"
             - wait for processes to stop"
             - continue with downtime regardless"
             - kill running processes   
            """),
            options,
            options + ['a', 'w', 'c', 'k']
        )
        if response in ('a', 'abort'):
            if ask('This will start all CommCare processes again. Do you want to proceed?'):
                downtime = get_downtime_record(environment)
                supervisor_services(environment, ansible_context, 'start')
                cancel_downtime_record(environment, downtime)
                return
        elif response in ('w', 'wait'):
            time.sleep(30)
        elif response in ('c', 'continue'):
            if ask('Are you sure you want to continue with downtime even though there '
                   'are still some processes running?'):
                return
        elif response in ('k', 'kill'):
            kill = ask('Are you sure you want to kill all remaining processes?', strict=True)
            if kill:
                kill_remaining_processes(environment, ansible_context)


def kill_remaining_processes(environment, ansible_context):
    command = 'pkill -u cchq -9; test $? -eq 0 -o $? -eq 1'
    return _run_command(environment, ansible_context, command, become=True)


def check_for_running_cchq_processes(environment, ansible_context, invert_success=True):
    command = 'ps -u cchq -U cchq -f'
    if invert_success:
        command = '{}; test $? -eq 1'.format(command)
    return _run_command(environment, ansible_context, command)


def supervisor_services(environment, ansible_context, action):
    return _run_command(environment, ansible_context, 'supervisorctl {} all'.format(action), become=True)


def _run_command(environment, ansible_context, command, become=False):
    return run_ansible_module(
        environment, ansible_context, HQ_PROCESSES_SCOPE, 'shell', command,
        become, None, False
    )


def print_downtime(downtime):
    end_ts = datetime.fromtimestamp(downtime['end']) if downtime['end'] else None
    puts("Downtime [{scope}] {state} from {start}{end}".format(
        state='active' if downtime['active'] else 'inactive',
        scope=', '.join(downtime['scope']),
        start=datetime.fromtimestamp(downtime['start']),
        end='to {end}'.format(end=end_ts) if end_ts else ''
    ))


def create_downtime_record(environment, message=None):
    # https://docs.datadoghq.com/api/?lang=python#schedule-monitor-downtime
    scope = 'environment:{}'.format(environment.meta_config.env_monitoring_id)
    if initialize_datadog(environment):
        if environment.meta_config.slack_alerts_channel:
            message = '{} @slack-{}'.format(message, environment.meta_config.slack_alerts_channel)

        downtime = datadog.api.Downtime.create(
            scope=scope,
            message=message
        )
    else:
        downtime = {
            'active': True,
            'message': message,
            'scope': [scope],
            'start': int(datetime.utcnow().strftime('%s')),
        }
    with open(environment.paths.downtime_yml, 'w') as f:
        yaml.safe_dump(downtime, f)
    return downtime


def cancel_downtime_record(environment, downtime):
    if 'id' in downtime and initialize_datadog(environment):
        datadog.api.Downtime.delete(downtime['id'])

    os.remove(environment.paths.downtime_yml)


def get_downtime_record(environment):
    if os.path.exists(environment.paths.downtime_yml):
        with open(environment.paths.downtime_yml, 'r') as f:
            return yaml.safe_load(f)


@memoized
def initialize_datadog(environment):
    datadog_enabled = environment.public_vars.get('DATADOG_ENABLED', False)
    if datadog_enabled:
        datadog.initialize(
            environment.get_vault_var('secrets.DATADOG_API_KEY'),
            environment.get_vault_var('secrets.DATADOG_APP_KEY')
        )
        return True
