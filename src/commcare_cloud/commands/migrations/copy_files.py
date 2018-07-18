import hashlib
import os

import attr
import yaml

from commcare_cloud.commands import shared_args
from commcare_cloud.commands.ansible.helpers import AnsibleContext, run_action_with_check_mode
from commcare_cloud.commands.ansible.run_module import run_ansible_module
from commcare_cloud.commands.command_base import CommandBase, Argument
from commcare_cloud.commands.utils import render_template
from commcare_cloud.environment.main import get_environment

FILE_MIGRATION_RSYNC_SCRIPT = 'file_migration_rsync.sh'
TEMPLATE_DIR = os.path.join(os.path.dirname(os.path.abspath(__file__)), 'templates')
REMOTE_MIGRATION_ROOT = 'file_migration'


@attr.s
class SourceFiles(object):
    source_host = attr.ib()
    source_dir = attr.ib()
    target_dir = attr.ib()
    files = attr.ib(factory=list)


class CopyFiles(CommandBase):
    command = 'copy-files'
    help = """
    Copy files from multiple sources to targets.

    This is a general purpose command that can be used to copy files between
    nodes in the cluster.
    """

    arguments = (
        Argument(dest='plan', help="Path to plan file"),
        Argument(dest='action', choices=['prepare', 'copy'], help="""
            Action to perform

            - prepare: generate the copy scripts and push them to the target servers
            - migrate: execute the copy scripts
        """),
        shared_args.SKIP_CHECK_ARG,
    )

    def run(self, args, unknown_args):
        environment = get_environment(args.env_name)
        environment.create_generated_yml()

        plan = read_plan(args.plan)
        working_directory = _get_working_dir(args.plan, environment)
        ansible_context = AnsibleContext(args)

        if args.action == 'prepare':
            for target_host, source_configs in plan.items():
                prepare_file_copy_scripts(target_host, source_configs, working_directory)
                copy_scripts_to_target_host(target_host, working_directory, environment, ansible_context)

        if args.action == 'copy':
            def run_check():
                return execute_file_copy_scripts(environment, list(plan), check_mode=True)

            def run_apply():
                return execute_file_copy_scripts(environment, list(plan), check_mode=False)

            return run_action_with_check_mode(run_check, run_apply, args.skip_check)


def read_plan(plan_path):
    with open(plan_path, 'r') as f:
        plan_dict = yaml.load(f)

    return {
        target_host: [
                SourceFiles(**config_dict) for config_dict in config_dicts
            ]
        for target in plan_dict['copy_files']
        for target_host, config_dicts in target.items()
    }


def _get_working_dir(plan_path, environment):
    plan_name = os.path.splitext(os.path.basename(plan_path))[0]
    dirname = "copy_file_scripts_{}_{}_tmp".format(environment.meta_config.deploy_env, plan_name)
    dir_path = os.path.join(os.path.dirname(self.plan_path), dirname)
    if not os.path.exists(dir_path):
        os.makedirs(dir_path)
    return dir_path


def prepare_file_copy_scripts(target_host, soucre_file_configs, script_root):
    target_script_root = os.path.join(script_root, target_host)
    if not os.path.exists(target_script_root):
        os.makedirs(target_script_root)

    files_for_node = []
    for config in soucre_file_configs:
        files = sorted(config.files)
        filename = get_file_list_filename(config)
        path = os.path.join(target_script_root, filename)
        with open(path, 'w') as f:
            f.write('{}\n'.format('\n'.join(files)))

        files_for_node.append((config, filename))

    if files_for_node:
        # create rsync script
        rsync_script_contents = render_template('file_migration_rsync.sh.j2', {
            'rsync_file_list': files_for_node,
            'rsync_file_root': os.path.join('/tmp', REMOTE_MIGRATION_ROOT)
        }, TEMPLATE_DIR)
        rsync_script_path = os.path.join(target_script_root, FILE_MIGRATION_RSYNC_SCRIPT)
        with open(rsync_script_path, 'w') as f:
            f.write(rsync_script_contents)


def copy_scripts_to_target_host(target_host, script_root, environment, ansible_context):
    local_files_path = os.path.join(script_root, target_host)

    destination_path = os.path.join('/tmp', REMOTE_MIGRATION_ROOT)

    # remove destination path to ensure we're starting fresh
    file_args = "path={} state=absent".format(destination_path)
    run_ansible_module(
        environment, ansible_context, target_host, 'file', file_args,
        True, None, False
    )

    # recursively copy all rsync file lists to destination
    copy_args = "src={src}/ dest={dest} mode={mode}".format(
        src=local_files_path,
        dest=destination_path,
        mode='0644'
    )
    run_ansible_module(
        environment, ansible_context, target_host, 'copy', copy_args,
        True, None, False
    )

    # make script executable
    file_args = "path={path} mode='0744'".format(
        path=os.path.join(destination_path, FILE_MIGRATION_RSYNC_SCRIPT)
    )
    run_ansible_module(
        environment, ansible_context, target_host, 'file', file_args,
        True, None, False
    )


def execute_file_copy_scripts(environment, target_hosts, check_mode=True):
    file_root = os.path.join('/tmp', REMOTE_MIGRATION_ROOT)
    run_parallel_command(
        environment,
        target_hosts,
        "{}{}".format(
            os.path.join(file_root, FILE_MIGRATION_RSYNC_SCRIPT),
            ' --dry-run' if check_mode else ''
        )
    )


def run_parallel_command(environment, hosts, command):
    from fabric.api import execute, sudo, env, parallel
    if env.ssh_config_path and os.path.isfile(os.path.expanduser(env.ssh_config_path)):
        env.use_ssh_config = True
    env.forward_agent = True
    env.sudo_prefix = "sudo -SE -p '%(sudo_prompt)s' "
    env.user = 'ansible'
    env.password = environment.get_ansible_user_password()
    env.hosts = hosts
    env.warn_only = True

    @parallel(pool_size=10)
    def _task():
        sudo(command)

    execute(_task)


def get_file_list_filename(config):
    dir_hash = hashlib.sha1('{}_{}'.format(config.source_dir, config.target_dir)).hexdigest()[:8]
    filename = '{}_{}__files'.format(config.source_host, dir_hash)
    return filename
