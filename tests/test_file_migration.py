import os
import shutil

from commcare_cloud.commands.migrations.copy_files import prepare_file_copy_scripts, SourceFiles, \
    FILE_MIGRATION_RSYNC_SCRIPT, get_file_list_filename
from tests.test_utils import get_file_contents

TEST_DATA_DIR = os.path.join(os.path.dirname(__file__), 'file_migration_data')
SCRIPT_ROOT = os.path.join(TEST_DATA_DIR, '.generated_data')


def tearDown():
    # delete generated files
    shutil.rmtree(SCRIPT_ROOT)


def test_prepare_migration_scripts():
    configs = [
        SourceFiles(
            'source_host1',
            'source_dir1',
            'target_dir1',
            ['file1', 'file2']
        ),
        SourceFiles(
            'source_host1',
            'source_dir2',
            'target_dir2',
            ['file3', 'file4']
        ),
        SourceFiles(
            'source_host2',
            'source_dir1',
            'target_dir1',
            ['file5', 'file6']
        )
    ]
    target_host = 'target_host1'
    script_path = prepare_file_copy_scripts(target_host, configs, SCRIPT_ROOT)
    check_file_contents(script_path, os.path.join(TEST_DATA_DIR, FILE_MIGRATION_RSYNC_SCRIPT))

    for config in configs:
        file_list_filename = get_file_list_filename(config)
        file_path = os.path.join(SCRIPT_ROOT, target_host, file_list_filename)
        file_list = get_file_contents(file_path).splitlines()
        assert file_list == config.files


def check_file_contents(generated_path, expected_path):
    expected_script = get_file_contents(expected_path)
    script_source = get_file_contents(generated_path)
    assert expected_script == script_source, "'{}'".format(script_source)
