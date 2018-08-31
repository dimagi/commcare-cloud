import os
import shutil

from mock import patch
from nose.tools import assert_multi_line_equal, assert_equal

from commcare_cloud.commands.migrations.copy_files import prepare_file_copy_scripts, SourceFiles, \
    FILE_MIGRATION_RSYNC_SCRIPT, get_file_list_filename, read_plan, Plan
from commcare_cloud.environment.main import get_environment
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
            rsync_args=['--checksum'],
            files=[],
            exclude=[]
        ),
        SourceFiles(
            'source_host1',
            'source_dir2',
            'target_dir2',
            files=['file3', 'file4'],
            exclude=[]
        ),
        SourceFiles(
            'source_host2',
            'source_dir1',
            'target_dir1',
            files=['file5', 'file6'],
            exclude=['logs/*', 'file.conf']
        )
    ]
    target_host = 'target_host1'
    prepare_file_copy_scripts(target_host, configs, SCRIPT_ROOT)
    _check_file_contents(
        os.path.join(SCRIPT_ROOT, target_host, FILE_MIGRATION_RSYNC_SCRIPT),
        os.path.join(TEST_DATA_DIR, FILE_MIGRATION_RSYNC_SCRIPT)
    )

    for config in configs[1:]:  # first config has no files list
        file_list_filename = get_file_list_filename(config)
        file_path = os.path.join(SCRIPT_ROOT, target_host, file_list_filename)
        file_list = get_file_contents(file_path).splitlines()
        assert_equal(file_list, config.files)


@patch('commcare_cloud.environment.paths.ENVIRONMENTS_DIR', TEST_DATA_DIR)
def test_parse_plan():
    target_env = get_environment('target_env')
    expected = Plan(
        source_env=get_environment('source_env'),
        configs={
            '10.0.0.1': [
                SourceFiles(
                    '192.168.33.15',
                    '/opt/data/',
                    '/opt/data/',
                    files=['test/']
                )
            ],
            '10.0.0.2': [
                SourceFiles(
                    '192.168.33.16',
                    '/opt/data/test/',
                    '/opt/data/',
                    rsync_args=['--checksum'],
                    files=['test/file1'],
                    exclude=['logs/*']
                )
            ]
        }
    )

    pla_path = os.path.join(TEST_DATA_DIR, 'test_plan.yml')
    plan = read_plan(pla_path, target_env)
    assert_equal(plan, expected)

    plan = read_plan(pla_path, target_env, 'target_host2')
    assert_equal(list(plan.configs), ['10.0.0.2'])


def _check_file_contents(generated_path, expected_path):
    expected_script = get_file_contents(expected_path)
    script_source = get_file_contents(generated_path)
    assert_multi_line_equal.__self__.maxDiff = None
    assert_multi_line_equal(expected_script.strip(), script_source.strip())
