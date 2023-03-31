from __future__ import absolute_import, unicode_literals

import hashlib
import os
import shutil
import subprocess
from io import open

import attr
import yaml

from commcare_cloud.commands import shared_args
from commcare_cloud.commands.ansible.helpers import (
    AnsibleContext,
    run_action_with_check_mode,
)
from commcare_cloud.commands.ansible.run_module import run_ansible_module, ansible_json
from commcare_cloud.commands.command_base import (
    Argument,
    CommandBase,
    CommandError,
)
from commcare_cloud.commands.utils import render_template
from commcare_cloud.environment.main import get_environment

FILE_MIGRATION_RSYNC_SCRIPT = 'file_migration_rsync.sh'
TEMPLATE_DIR = os.path.join(os.path.dirname(os.path.abspath(__file__)), 'templates')
REMOTE_MIGRATION_ROOT = '/tmp/file_migration'


@attr.s
class Plan(object):
    source_env = attr.ib()
    configs = attr.ib()


@attr.s
class SourceFiles(object):
    source_host = attr.ib()
    source_dir = attr.ib()
    target_dir = attr.ib()
    source_user = attr.ib(default='ansible')
    files = attr.ib(factory=list)
    exclude = attr.ib(factory=list)
    rsync_args = attr.ib(factory=list)


class CopyFiles(CommandBase):
    command = 'copy-files'
    help = """
    Copy files from multiple sources to targets.

    This is a general purpose command that can be used to copy files between
    hosts in the cluster.

    Files are copied using `rsync` from the target host. This tool assumes that the
    specified user on the source host has permissions to read the files being copied.

    The plan file must be formatted as follows:

    ```yml
    source_env: env1 (optional if source is different from target;
                      SSH access must be allowed from the target host(s) to source host(s))
    copy_files:
      - <target-host>:
          - source_host: <source-host>
            source_user: <user>
            source_dir: <source-dir>
            target_dir: <target-dir>
            rsync_args: []
            files:
              - test/
              - test1/test-file.txt
            exclude:
              - logs/*
              - test/temp.txt
    ```
    - **copy_files**: Multiple target hosts can be listed.
    - **target-host**: Hostname or IP of the target host. Multiple source
      definitions can be listed for each target host.
    - **source-host**: Hostname or IP of the source host.
    - **source-user**: (optional) User to ssh as from target to source. Defaults
      to 'ansible'. This user must have permissions to read the files being
      copied.
    - **source-dir**: The base directory from which all source files referenced.
    - **target-dir**: Directory on the target host to copy the files to.
    - **rsync_args**: Additional arguments to pass to rsync.
    - **files**: List of files to copy. File paths are relative to `source-dir`.
      Directories can be included and must end with a `/`.
    - **exclude**: (optional) List of relative paths to exclude from the
      *source-dir*. Supports wildcards e.g. "logs/*".
    """

    arguments = (
        Argument(dest='plan_path', help="Path to plan file"),
        Argument(dest='action', choices=['prepare', 'copy', 'cleanup'], help="""
            Action to perform

            - prepare: generate the scripts and push them to the target servers
            - copy: execute the scripts
            - cleanup: remove temporary files and remote auth
        """),
        shared_args.LIMIT_ARG,
        shared_args.SKIP_CHECK_ARG,
    )

    def run(self, args, unknown_args):
        ansible_context = AnsibleContext(args)
        environment = ansible_context.environment

        plan = read_plan(args.plan_path, environment, args.limit)
        working_directory = _get_working_dir(args.plan_path, environment)

        environment.secrets_backend.prompt_user_input()
        if plan.source_env != environment and args.action in ('prepare', 'cleanup'):
            plan.source_env.secrets_backend.prompt_user_input()

        if args.action == 'prepare':
            for target_host, source_configs in plan.configs.items():
                self.log("Creating scripts to copy files.")
                prepare_file_copy_scripts(target_host, source_configs, working_directory)
                self.log("Moving scripts to target hosts.")
                copy_scripts_to_target_host(target_host, working_directory, ansible_context)
            self.log("Establishing auth between target and source.")
            setup_auth(plan, ansible_context, working_directory)

        if args.action == 'copy':
            def run_check():
                return execute_file_copy_scripts(ansible_context, limit, check_mode=True)

            def run_apply():
                return execute_file_copy_scripts(ansible_context, limit, check_mode=False)

            limit = args.limit or ",".join(plan.configs)
            return run_action_with_check_mode(run_check, run_apply, args.skip_check)

        if args.action == 'cleanup':
            for target_host in plan.configs:
                remove_scripts(target_host, ansible_context)
            teardown_auth(plan, ansible_context, working_directory)
            shutil.rmtree(working_directory)


def read_plan(plan_path, target_env, limit=None):
    with open(plan_path, 'r', encoding='utf-8') as f:
        # PY2: yaml.safe_load returns byte strings when the content is ASCII-only bytes
        plan_dict = yaml.safe_load(f)

    source_env = None
    if 'source_env' in plan_dict:
        source_env = get_environment(plan_dict['source_env'])
    else:
        source_env = target_env

    def _get_source_files(config_dict):
        config_dict['source_host'] = source_env.translate_host(config_dict['source_host'], plan_path)
        return SourceFiles(**config_dict)

    configs = {
        target_env.translate_host(target_host, plan_path): [
            _get_source_files(config_dict) for config_dict in config_dicts
        ]
        for target in plan_dict['copy_files']
        for target_host, config_dicts in target.items()
    }
    if limit:
        subset = [host.name for host in target_env.inventory_manager.get_hosts(limit)]
        configs = {
            host: config
            for host, config in configs.items()
            if host in subset
        }
    if not configs:
        raise CommandError("Limit pattern did not match any hosts: {}".format(limit))

    return Plan(
        source_env=source_env or target_env,
        configs=configs
    )


def _get_working_dir(plan_path, environment):
    plan_name = os.path.splitext(os.path.basename(plan_path))[0]
    dirname = "copy_file_scripts_{}_{}_tmp".format(environment.meta_config.deploy_env, plan_name)
    dir_path = os.path.join(os.path.dirname(plan_path), dirname)
    if not os.path.exists(dir_path):
        os.makedirs(dir_path)
    return dir_path


def prepare_file_copy_scripts(target_host, source_file_configs, script_root):
    target_script_root = os.path.join(script_root, target_host)
    if not os.path.exists(target_script_root):
        os.makedirs(target_script_root)

    files_for_node = []
    for config in source_file_configs:
        files = sorted(config.files)
        if not files:
            files_for_node.append((config, None))
        else:
            filename = get_file_list_filename(config)
            path = os.path.join(target_script_root, filename)
            with open(path, 'w', encoding='utf-8') as f:
                # PY2: unicode literals will coerce bytes -> unicode on py2
                f.write('{}\n'.format('\n'.join(files)))

            files_for_node.append((config, filename))

    if files_for_node:
        # create rsync script
        rsync_script_contents = render_template('file_migration_rsync.sh.j2', {
            'rsync_file_list': files_for_node,
            'rsync_file_root': REMOTE_MIGRATION_ROOT
        }, TEMPLATE_DIR)
        rsync_script_path = os.path.join(target_script_root, FILE_MIGRATION_RSYNC_SCRIPT)
        with open(rsync_script_path, 'w', encoding='utf-8') as f:
            f.write(rsync_script_contents)


def copy_scripts_to_target_host(target_host, script_root, ansible_context):
    local_files_path = os.path.join(script_root, target_host)

    # remove destination path to ensure we're starting fresh
    remove_scripts(target_host, ansible_context)

    # recursively copy all rsync file lists to destination
    copy_args = "src={src}/ dest={dest} mode={mode}".format(
        src=local_files_path,
        dest=REMOTE_MIGRATION_ROOT,
        mode='0644'
    )
    run_ansible_module(ansible_context, target_host, 'copy', copy_args)

    # make script executable
    file_args = "path={path} mode='0744'".format(
        path=os.path.join(REMOTE_MIGRATION_ROOT, FILE_MIGRATION_RSYNC_SCRIPT)
    )
    run_ansible_module(ansible_context, target_host, 'file', file_args)


def remove_scripts(target_host, ansible_context):
    args = "path={} state=absent".format(REMOTE_MIGRATION_ROOT)
    run_ansible_module(ansible_context, target_host, 'file', args)


def execute_file_copy_scripts(ansible_context, limit, check_mode=True):
    script = os.path.join(REMOTE_MIGRATION_ROOT, FILE_MIGRATION_RSYNC_SCRIPT)
    try:
        run_ansible_module(
            ansible_context,
            'all',
            'shell',
            script + (' --dry-run' if check_mode else ''),
            extra_args=('--limit=' + limit,),
            run_command=subprocess.check_call,
        )
    except subprocess.CalledProcessError as err:
        return err.returncode
    return 0


def get_file_list_filename(config):
    data = '{}_{}'.format(config.source_dir, config.target_dir).encode("utf8")
    dir_hash = hashlib.sha1(data).hexdigest()[:8]
    filename = '{}_{}__files'.format(config.source_host, dir_hash)
    return filename


def setup_auth(plan, ansible_context, working_directory):
    _run_auth_playbook(plan, ansible_context, 'add', working_directory)


def teardown_auth(plan, ansible_context, working_directory):
    _run_auth_playbook(plan, ansible_context, 'remove', working_directory)


def _run_auth_playbook(plan, ansible_context, action, working_directory):
    auth_pairs = set()
    for target_host, source_configs in plan.configs.items():
        auth_pairs.update({
            (target_host, config.source_host, config.source_user) for config in source_configs
        })

    for target_host, source_host, source_user in auth_pairs:
        _set_auth_key(
            AnsibleContext(None, plan.source_env),
            source_host,
            source_user,
            ansible_context,  # target_context
            target_host,
            working_directory,
            remove=(action == 'remove'),
        )


def _set_auth_key(source_context, source_host, source_user,
                  target_context, target_host, working_directory, remove=False):
    target_user = "root"
    key_path = os.path.join(working_directory, 'id_rsa_{}.pub'.format(target_host))
    if not remove:
        user_args = "name={} generate_ssh_key=yes".format(target_user)
        data = run_ansible_module(target_context, target_host, 'user', user_args, run_command=ansible_json)
        with open(key_path, "w") as fh:
            fh.write(data[target_host]["ssh_public_key"])

    state = 'absent' if remove else 'present'
    args = "user={} state={} key={{{{ lookup('file', '{}') }}}}".format(source_user, state, key_path)
    run_ansible_module(source_context, source_host, 'authorized_key', args)

    if remove:
        os.remove(key_path)
