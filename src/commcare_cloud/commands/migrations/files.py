import hashlib
import os

import attr

from commcare_cloud.commands.ansible.run_module import run_ansible_module
from commcare_cloud.commands.utils import render_template

FILE_MIGRATION_RSYNC_SCRIPT = 'file_migration_rsync.sh'
TEMPLATE_DIR = os.path.join(os.path.dirname(os.path.abspath(__file__)), 'templates')
REMOTE_MIGRATION_ROOT = 'file_migration'


@attr.s
class MigrationFiles(object):
    source_host = attr.ib()
    source_dir = attr.ib()
    target_dir = attr.ib()
    files = attr.ib(factory=list)


def prepare_migration_scripts(target_host, migration_configs, script_root):
    target_script_root = os.path.join(script_root, target_host)
    if not os.path.exists(target_script_root):
        os.makedirs(target_script_root)

    files_for_node = []
    for config in migration_configs:
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

        return rsync_script_path


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


def get_file_list_filename(config):
    dir_hash = hashlib.sha1('{}_{}'.format(config.source_dir, config.target_dir)).hexdigest()[:8]
    filename = '{}_{}__files'.format(config.source_host, dir_hash)
    return filename
