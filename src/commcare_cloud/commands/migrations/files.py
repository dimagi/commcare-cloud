import hashlib
import os

import attr

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


def prepare_migration_script(target_host, migration_configs, script_root):
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


def get_file_list_filename(config):
    dir_hash = hashlib.sha1('{}_{}'.format(config.source_dir, config.target_dir)).hexdigest()[:8]
    filename = '{}_{}__files'.format(config.source_host, dir_hash)
    return filename
