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


class DatadogMonitors(CommandBase):
    command = 'update-datadog-monitors'
    help = """Update Datadog Monitor definitions"""

    arguments = (
        Argument('config'),
        Argument('-k', '--update-key', nargs='*', choices=UPDATE_KEYS, help="Only update these keys."),
    )

    def run(self, args, unknown_args):
        with open(args.config, 'r') as config_file:
            config = Config(yaml.load(config_file))
            config.env_notifications = OrderedDict(sorted(config.env_notifications.items()))

        keys_to_update = args.update_key or UPDATE_KEYS
        env = get_environment(config.env_with_datadog_auth)
        monitors = get_monitor_definitions(config)
        initialize(
            api_key=env.get_vault_var('secrets.DATADOG_API_KEY'),
            app_key=env.get_vault_var('secrets.DATADOG_APP_KEY')
        )
        any_diffs = False
        missing_monitors = {raw_mon['id']: raw_mon for raw_mon in api.Monitor.get_all()}
        for id, mon in monitors.items():
            raw_mon = api.Monitor.get(id)
            if raw_mon.get('errors'):
                puts(colored.magenta(
                    "\nError for '{}': {}\n".format(mon['name'], raw_mon['errors'])
                ))
                continue
            else:
                del missing_monitors[id]
            cleaned = clean_raw_monitor(raw_mon)
            expected = get_data_to_update(mon, keys_to_update)
            actual = get_data_to_update(cleaned, keys_to_update)
            diff = list(_unidiff_output(yaml.safe_dump(actual), yaml.safe_dump(expected)))
            any_diffs |= bool(diff)
            if diff:
                puts(colored.magenta("\nDiff for '{}'\n".format(mon['name'])))
                with indent():
                    print_diff(diff)

        if missing_monitors:
            puts(colored.magenta(
                "FYI you also have some untracked monitors. "
                "No change will be applied for these:"
            ))
            for id, raw_mon in sorted(missing_monitors.items()):
                puts(colored.magenta("  - Untracked monitor {} '{}' (no change will be applied)".format(id, raw_mon['name'])))

        if any_diffs:
            if ask("Do you want to push these changes to Datadog?"):
                for id, mon in monitors.items():
                    to_update = get_data_to_update(mon, keys_to_update)
                    api.Monitor.update(id, **to_update)
