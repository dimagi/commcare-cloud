from pathlib import Path

from commcare_cloud.environment.main import Environment
from commcare_cloud.environment.paths import DefaultPaths

ENVS_DIR = Path(__file__).parent.parent / '.travis/environments'


def test_python_version():
    env = Environment(DefaultPaths('travis', environments_dir=ENVS_DIR))
    assert 'python_version' not in env.public_vars, env.public_vars['python_version']
    assert env.python_version == env.group_vars["python_version"], \
        (env.python_version, env.group_vars["python_version"])
