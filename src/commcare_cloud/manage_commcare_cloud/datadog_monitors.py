from __future__ import absolute_import
from __future__ import print_function
import difflib
import os
import re
from abc import ABCMeta, abstractmethod

import jinja2
import six
import yaml
from clint.textui import puts, indent
from datadog import api, initialize
from jinja2 import DictLoader
from jsonobject.api import JsonObject
from jsonobject.properties import StringProperty, DictProperty
from memoized import memoized
from simplejson import OrderedDict

from commcare_cloud.cli_utils import ask
from commcare_cloud.colors import color_added, color_removed, color_unchanged, color_warning, \
    color_notice
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


def render_notification_block(config, env_key, skip_envs=None):
    j2 = get_datadog_jinja_environment()
    template = j2.get_template('notification_block.j2')
    envs = config.env_notifications
    if skip_envs:
        # copy but maintain ordering
        envs = OrderedDict(sorted(config.env_notifications.items()))
        for env in skip_envs:
            envs.pop(env, None)
    return template.render(
        env_key=env_key,
        catchall_alert_channel=config.catchall_alert_channel,
        envs=envs,
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
            puts(color_added(line), newline=False)
        elif line.startswith('-'):
            puts(color_removed(line), newline=False)
        elif line.startswith('@@'):
            puts(color_unchanged(line), newline=False)
        else:
            puts(line, newline=False)


def get_monitor_definitions(config):
    monitors = {}
    monitor_file_names_by_id = {}
    for file in os.listdir(CONFIG_ROOT):
        if file.endswith('yml') and file != '.ignore.yml':
            file_path = os.path.join(CONFIG_ROOT, file)
            with open(file_path, 'r') as mon:
                data = mon.read()
            monitor_def = render_messages(config, yaml.safe_load(data))
            monitors[monitor_def['id']] = monitor_def
            monitor_file_names_by_id[monitor_def['id']] = file_path
    return monitors, monitor_file_names_by_id


def dump_monitor_yaml(monitor_definition):
    return yaml.safe_dump(monitor_definition, allow_unicode=True)


def write_monitor_definition(monitor_id, monitor_definition):
    if 'env_key' not in monitor_definition:
        # try to guess it
        for env_key in ['environment.name', 'host.environment']:
            if env_key in monitor_definition['message']:
                monitor_definition['env_key'] = env_key
                break
        else:
            if 'by {environment}' in monitor_definition['query']:
                monitor_definition['env_key'] = 'environment.name'
            else:
                monitor_definition['env_key'] = 'host.environment'

    filename = 'autogen_{}.yml'.format(monitor_id)
    with open(os.path.join(CONFIG_ROOT, filename), 'w') as f:
        f.write(dump_monitor_yaml(monitor_definition))


def get_ignored_mointor_ids():
    with open(os.path.join(CONFIG_ROOT, '.ignore.yml'), 'r') as f:
        return yaml.safe_load(f)['ignored_monitors']


def render_messages(config, monitor):
    monitor = monitor.copy()
    env_key = monitor['env_key']
    skip_envs = monitor.get('skip_envs', [])
    message_rendered = render_message(config, monitor['message'], env_key, skip_envs)
    monitor['message'] = LiteralUnicode(message_rendered.strip())
    escal_msg = monitor['options'].get(ESCAL_MSG)
    if escal_msg:
        elcal_rendered = render_message(config, escal_msg, env_key, skip_envs)
        monitor['options'][ESCAL_MSG] = LiteralUnicode(elcal_rendered.strip())
    if 'include_tags' not in monitor['options']:
        monitor['options']['include_tags'] = True
    return monitor


def render_message(config, message, env_key, skip_envs=None):
    j2 = jinja2.Environment(loader=DictLoader({'m': message}), **JINJA_OPTS)
    return j2.get_template('m').render(
        notification_block=render_notification_block(config, env_key, skip_envs)
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
        config = Config(yaml.safe_load(config_file))
        config.env_notifications = OrderedDict(sorted(config.env_notifications.items()))
    return config


class MonitorError(Exception):
    pass


class MonitorAPI(six.with_metaclass(ABCMeta)):
    def __init__(self, filtered_ids=None):
        self.filtered_ids = filtered_ids

    @abstractmethod
    def get_all(self):
        raise NotImplementedError

    def get_filtered(self):
        all_monitors = self.get_all()
        if not self.filtered_ids:
            return all_monitors
        else:
            return {
                mid: all_monitors[mid] for mid in self.filtered_ids
            }


class RemoteMonitorAPI(MonitorAPI):
    def _wrap(self, raw_mon):
        # This drove me crazy to figure out, but the get_all endpoint omits
        # options.synthetics_check_id for no reason I can think of.
        # If it's a synthetics alert, pull it again directly by id.
        if raw_mon['type'] == 'synthetics alert':
            raw_mon = api.Monitor.get(raw_mon['id'])
        if raw_mon.get('errors'):
            raise MonitorError('\n'.join(raw_mon['errors']))
        else:
            return clean_raw_monitor(raw_mon)

    def get_all(self):
        return {raw_mon['id']: self._wrap(raw_mon) for raw_mon in api.Monitor.get_all()
                if raw_mon['id'] not in get_ignored_mointor_ids()}

    def update(self, monitor_id, wrapped_monitor):
        result = api.Monitor.update(monitor_id, **wrapped_monitor)
        if result.get('errors'):
            raise MonitorError('\n'.join(result['errors']))


class LocalMonitorAPI(MonitorAPI):
    def __init__(self, config, filtered_ids=None):
        super(LocalMonitorAPI, self).__init__(filtered_ids=filtered_ids)
        self.config = config
        self._monitors_by_id = None
        self._monitor_file_names_by_id = None

    @memoized
    def _load_monitors(self):
        self._monitors, self._monitor_file_names_by_id = get_monitor_definitions(self.config)

    def get_all(self):
        self._load_monitors()
        return self._monitors

    def get_filename_for_monitor(self, monitor_id):
        self._load_monitors()
        return self._monitor_file_names_by_id[monitor_id]

    def create(self, monitor_id, wrapped_monitor):
        write_monitor_definition(monitor_id, wrapped_monitor)


class UpdateDatadogMonitors(CommandBase):
    command = 'update-datadog-monitors'
    help = """Update Datadog Monitor definitions"""

    arguments = (
        Argument('config'),
        Argument('-k', '--update-key', nargs='*', choices=UPDATE_KEYS, help="Only update these keys."),
        Argument('-m', '--monitors', type=int, nargs='*', help="Only update these monitors (by id)."),
    )

    def run(self, args, unknown_args):
        config = get_config(args.config)
        keys_to_update = args.update_key or UPDATE_KEYS
        initialize_datadog(config)
        remote_monitor_api = RemoteMonitorAPI(filtered_ids=args.monitors)
        local_monitor_api = LocalMonitorAPI(config, filtered_ids=args.monitors)

        local_monitors = local_monitor_api.get_filtered()
        remote_monitors = remote_monitor_api.get_filtered()

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

        monitors_with_diffs = {}

        any_diffs = False
        if only_local:
            for id, monitor in only_local.items():
                puts(color_warning(
                    "\nMonitor missing from datadog: {} ({})\n".format(monitor['name'], id)
                ))

        for id, (expected, actual) in shared_local_remote_monitors.items():
            diff = list(_unidiff_output(
                dump_monitor_yaml(get_data_to_update(actual, keys_to_update)),
                dump_monitor_yaml(get_data_to_update(expected, keys_to_update))))
            any_diffs |= bool(diff)
            if diff:
                puts(color_notice("\nDiff for '{}'".format(expected['name'])))
                puts(local_monitor_api.get_filename_for_monitor(expected['id']))

                with indent():
                    print_diff(diff)
                monitors_with_diffs[id] = expected

        if any_diffs:
            if ask("Do you want to push these changes to Datadog?"):
                for id, expected in monitors_with_diffs.items():
                    print(("Updating '{}'".format(expected['name'])))
                    remote_monitor_api.update(id, get_data_to_update(expected, keys_to_update))

        if only_remote:
            puts(color_warning(
                "FYI you also have some untracked monitors. "
                "No change will be applied for these:"
            ))
            for id, missing_monitor in sorted(only_remote.items()):
                puts("  - Untracked monitor {} '{}' (no change will be applied)".format(id, missing_monitor['name']))
            if ask("And BTW do you want to dump all untracked monitors as a starting point?"):
                for id, missing_monitor in sorted(only_remote.items()):
                    local_monitor_api.create(id, missing_monitor)


class ListDatadogMonitors(CommandBase):
    command = 'list-datadog-monitors'
    help = """Lost Datadog Monitor definitions"""

    arguments = (
        Argument('config'),
        Argument('-f', '--filenames', action='store_true', help="Show filenames instead of monitor names."),
        Argument('-l', '--local', action='store_true', help="Only list what's local. Don't query Datadog."),
        Argument('--sort', choices=('name', 'id'), default='id', help="Sort order."),
    )

    def run(self, args, unknown_args):
        config = get_config(args.config)
        local_monitor_api = LocalMonitorAPI(config)

        show_filenames = args.filenames
        sort_index = {
            'id': 0,
            'name': 1
        }[args.sort]

        def _print(title, monitors):
            _print_monitors(local_monitor_api, title, monitors, show_filenames, sort_index)

        local_monitors = local_monitor_api.get_all()
        if args.local:
            _print("\nMonitors", local_monitors)
        else:
            initialize_datadog(config)
            remote_monitor_api = RemoteMonitorAPI()
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
                id: local_monitors[id]
                for id in set(local_monitors) & set(remote_monitors)
            }

            _print("\nMonitors", shared_local_remote_monitors)
            _print("\nMonitors only on Datadog", only_remote)
            _print("\nMonitors only on local", only_local)


def _print_monitors(api, title, monitors, show_filenames, sort_index):
    if not monitors:
        return
    puts(title)
    with indent():
        output_list = sorted([
            (id, _get_display(api, monitor, show_filenames))
            for id, monitor in monitors.items()
        ], key=lambda p: p[sort_index])
        for id, name in output_list:
            puts("{:<10}: {}".format(id, name))


def _get_display(api, monitor, show_filenames):
    name_ = monitor['name']
    if show_filenames:
        try:
            name_ = api.get_filename_for_monitor(monitor['id'])
            _, name_ = os.path.split(name_)
        except KeyError:
            pass
    return name_
