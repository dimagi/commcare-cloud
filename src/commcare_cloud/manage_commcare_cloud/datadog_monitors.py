import difflib
import os
import re

import jinja2
import yaml
from clint.textui import puts, colored, indent
from datadog import api, initialize
from jinja2 import DictLoader
from jsonobject.api import JsonObject
from jsonobject.properties import StringProperty, DictProperty
from memoized import memoized
from simplejson import OrderedDict

from commcare_cloud.cli_utils import ask
from commcare_cloud.commands.command_base import CommandBase, Argument
from commcare_cloud.environment.main import get_environment
from commcare_cloud.manage_commcare_cloud.yaml_representers import LiteralUnicode

ESCAL_MSG = 'escalation_message'

CONFIG_ROOT = os.path.join(os.path.dirname(__file__), 'monitors')


KEYS_OF_INTEREST = [
    "id",
    "name",
    "tags",
    "query",
    "message",
    "options",
    "type"
]

UPDATE_KEYS = list(set(KEYS_OF_INTEREST) - {'id', 'type'} | {ESCAL_MSG})

JINJA_OPTS = {
    "block_start_string": "<%",
    "block_end_string": "%>",
    "variable_start_string": "<<",
    "variable_end_string": ">>",
    "comment_start_string": "<#",
    "comment_end_string": "#>",
}

BLOCK = '{{{{is_match "{env_key}" }}}}{start_or_end} NOTIFCATION_BLOCK{{{{/is_match}}}}'


def make_string_yaml_safe(string):
    string = string.replace('\t', ' ' * 4)
    return re.sub(r'\s*\n', '\n', string)


class Config(JsonObject):
    env_with_datadog_auth = StringProperty(required=True)
    catchall_alert_channel = StringProperty(required=True)
    env_notifications = DictProperty(required=True)


@memoized
def get_datadog_jinja_environment():
    return jinja2.Environment(
        loader=jinja2.FileSystemLoader(CONFIG_ROOT),
        **JINJA_OPTS
    )


def render_notification_block(config, env_key):
    j2 = get_datadog_jinja_environment()
    template = j2.get_template('notification_block.j2')
    return template.render(
        env_key=env_key,
        catchall_alert_channel=config.catchall_alert_channel,
        envs=config.env_notifications,
        start_block=BLOCK.format(env_key=env_key, start_or_end='START'),
        end_block=BLOCK.format(env_key=env_key, start_or_end='END'),
    )


def clean_raw_monitor(raw):
    cleaned = {k: raw[k] for k in KEYS_OF_INTEREST}
    cleaned['message'] = LiteralUnicode(make_string_yaml_safe(cleaned['message']))
    escalation_message = cleaned['options'].get(ESCAL_MSG)
    if escalation_message:
        safe = make_string_yaml_safe(escalation_message)
        cleaned['options'][ESCAL_MSG] = LiteralUnicode(safe)
    return cleaned


def _unidiff_output(expected, actual):
    """
    Helper function. Returns a string containing the unified diff of two multiline strings.
    """
    expected = expected.splitlines(1)
    actual = actual.splitlines(1)
    return difflib.unified_diff(expected, actual)


def print_diff(diff_lines):
    for line in diff_lines:
        if line.startswith('+'):
            puts(colored.green(line), newline=False)
        elif line.startswith('-'):
            puts(colored.red(line), newline=False)
        elif line.startswith('@@'):
            puts(colored.cyan(line), newline=False)
        else:
            puts(line, newline=False)


def get_monitor_definitions(config):
    monitors = {}
    for file in os.listdir(CONFIG_ROOT):
        if file.endswith('yml'):
            with open(os.path.join(CONFIG_ROOT, file), 'r') as mon:
                data = mon.read()
            monitor_def = render_messages(config, yaml.load(data))
            monitors[monitor_def['id']] = monitor_def
    return monitors


def write_monitor_definition(monitor_id, monitor_definition):
    if 'env_key' not in monitor_definition:
        # try to guess it
        for env_key in ['environment.name', 'host.environment']:
            if env_key in monitor_definition['message']:
                monitor_definition['env_key'] = env_key
                break
        if 'by {environment}' in monitor_definition['query']:
            monitor_definition['env_key'] = 'environment.name'
        else:
            monitor_definition['env_key'] = 'host.environment'

    filename = 'autogen_{}.yml'.format(monitor_id)
    with open(os.path.join(CONFIG_ROOT, filename), 'w') as f:
        f.write(yaml.safe_dump(monitor_definition, allow_unicode=True))


def render_messages(config, monitor):
    monitor = monitor.copy()
    message_rendered = render_message(config, monitor['message'], monitor['env_key'])
    monitor['message'] = LiteralUnicode(message_rendered.strip())
    escal_msg = monitor['options'].get(ESCAL_MSG)
    if escal_msg:
        elcal_rendered = render_message(config, escal_msg, monitor['env_key'])
        monitor['options'][ESCAL_MSG] = LiteralUnicode(elcal_rendered.strip())
    return monitor


def render_message(config, message, env_key):
    j2 = jinja2.Environment(loader=DictLoader({'m': message}), **JINJA_OPTS)
    return j2.get_template('m').render(
        notification_block=render_notification_block(config, env_key)
    )


def get_data_to_update(monitor, keys_to_update):
    to_update = {
        key: val for key, val in monitor.items()
        if key in keys_to_update
    }
    if ESCAL_MSG in keys_to_update:
        msg = monitor['options'].get(ESCAL_MSG)
        if msg:
            opts = to_update.get('options', {})
            opts[ESCAL_MSG] = msg
            to_update['options'] = opts
    return to_update


def initialize_datadog(config):
    env = get_environment(config.env_with_datadog_auth)
    initialize(
        api_key=env.get_vault_var('secrets.DATADOG_API_KEY'),
        app_key=env.get_vault_var('secrets.DATADOG_APP_KEY')
    )


def get_config(config_path):
    with open(config_path, 'r') as config_file:
        config = Config(yaml.load(config_file))
        config.env_notifications = OrderedDict(sorted(config.env_notifications.items()))
    return config


class MonitorError(Exception):
    def __init__(self, errors):
        self.errors = errors


class RemoteMonitorAPI(object):
    def __init__(self, keys_to_update):
        self.keys_to_update = keys_to_update

    def _wrap(self, raw_mon):
        if raw_mon.get('errors'):
            raise MonitorError(raw_mon['errors'])
        else:
            return clean_raw_monitor(raw_mon)

    def get_all(self):
        return {raw_mon['id']: self._wrap(raw_mon) for raw_mon in api.Monitor.get_all()}

    def update(self, monitor_id, wrapped_monitor):
        api.Monitor.update(monitor_id, **wrapped_monitor)


class LocalMonitorAPI(object):
    def __init__(self, config, keys_to_update):
        self.config = config
        self.keys_to_update = keys_to_update

    def get_all(self):
        return get_monitor_definitions(self.config)

    def create(self, monitor_id, wrapped_monitor):
        write_monitor_definition(monitor_id, wrapped_monitor)


class DatadogMonitors(CommandBase):
    command = 'update-datadog-monitors'
    help = """Update Datadog Monitor definitions"""

    arguments = (
        Argument('config'),
        Argument('-k', '--update-key', nargs='*', choices=UPDATE_KEYS, help="Only update these keys."),
    )

    def run(self, args, unknown_args):
        config = get_config(args.config)
        keys_to_update = args.update_key or UPDATE_KEYS
        initialize_datadog(config)
        remote_monitor_api = RemoteMonitorAPI(keys_to_update)
        local_monitor_api = LocalMonitorAPI(config, keys_to_update)

        local_monitors = local_monitor_api.get_all()
        remote_monitors = remote_monitor_api.get_all()

        only_remote = {
            id: remote_monitors[id]
            for id in set(remote_monitors) - set(local_monitors)
        }
        only_local = {
            id: local_monitors[id]
            for id in set(local_monitors) - set(remote_monitors)
        }
        shared_local_remote_monitors = {
            id: (local_monitors[id], remote_monitors[id])
            for id in set(local_monitors) & set(remote_monitors)
        }

        any_diffs = False
        if only_local:
            for id, monitor in only_local.items():
                puts(colored.magenta(
                    "\nMonitor missing from datadog: {} ({})\n".format(monitor['name'], id)
                ))

        for id, (expected, actual) in shared_local_remote_monitors.items():
            diff = list(_unidiff_output(
                yaml.safe_dump(get_data_to_update(actual, keys_to_update)),
                yaml.safe_dump(get_data_to_update(expected, keys_to_update))))
            any_diffs |= bool(diff)
            if diff:
                puts(colored.magenta("\nDiff for '{}'\n".format(expected['name'])))
                with indent():
                    print_diff(diff)

        if any_diffs:
            if ask("Do you want to push these changes to Datadog?"):
                for id, expected in local_monitors.items():
                    remote_monitor_api.update(id, expected)

        if only_remote:
            puts(colored.magenta(
                "FYI you also have some untracked monitors. "
                "No change will be applied for these:"
            ))
            for id, missing_monitor in sorted(only_remote.items()):
                puts(colored.magenta("  - Untracked monitor {} '{}' (no change will be applied)".format(id, missing_monitor['name'])))
            if ask("And BTW do you want to dump all untracked monitors as a starting point?"):
                for id, missing_monitor in sorted(only_remote.items()):
                    local_monitor_api.create(id, missing_monitor)
