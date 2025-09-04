#! /usr/bin/env python3
from pathlib import Path

from ansible.module_utils.basic import AnsibleModule

__metaclass__ = type


DOCUMENTATION = """
---
module: setup_virtualenv

short_description: Setup virtualenv for a software release.

version_added: "1.0.0"

description: Create a virtualenv for a software release. Use
    'virtualenv-clone' to copy the virtualenv from a previous release
    as a starting point. Then update requirements with 'pip-sync'.

options:
    dest:
        description: Directory path in which to create the new virtualenv.
        required: true
        type: str
    env_name:
        description: Virtualenv base name. The python version is added
            to the virtualenv name, and a symlink is created linking the
            base name to the virtualenv directory. Default: 'python_env'
        required: false
        default: 'python_env'
        type: str
    http_proxy:
        description: HTTP proxy address.
        required: false
        type: str

extends_documentation_fragment:
    - commcare_cloud.ansible

author:
    - Daniel Miller (@millerdev)
"""

EXAMPLES = """
- name: Setup virtualenv
  setup_virtualenv:
    dest: "/path/to/releases/next"
"""

RETURN = """
changed:
    description: Changed flag.
    type: bool
diff:
    description: Dict of before and after states of the virtualenv.
    type: dict
    sample: {'before': {'path': ...}, 'after': {'path': ...}}
venv:
    description: Path of the new virtualenv.
    type: str
    sample: /path/to/releases/next/python_env
"""


def main():
    module_args = {
        'dest': {'type': 'str', 'required': True},
        'env_name': {'type': 'str', 'default': 'python_env'},
        'http_proxy': {'type': 'str', 'default': None},
    }
    module = AnsibleModule(
        argument_spec=module_args,
        supports_check_mode=True
    )
    params = module.params
    env_name = params["env_name"]
    assert env_name != ".venv"
    dest = Path(params["dest"])
    next_env = dest / ".venv"
    python_env = dest / env_name
    proxy = params["http_proxy"]

    diff = {'before': {}, 'after': {'path': str(python_env)}}
    result = {'changed': False, 'venv': str(python_env), 'diff': diff}

    if not python_env.exists():
        result["changed"] = True
        if not module.check_mode:
            uv_sync(dest, proxy, module)
            assert next_env.is_dir(), f"uv did not create {next_env}"
            python_env.symlink_to(".venv")

    module.exit_json(**result)


def uv_sync(dest, proxy, module):
    proxy_env = {"ALL_PROXY": proxy} if proxy else {}
    module.run_command(
        ["uv", "sync", "--group=prod", "--no-dev", "--locked", "--compile-bytecode"],
        environ_update={"UV_HTTP_TIMEOUT": "60", **proxy_env},
        cwd=dest,
        check_rc=True,
    )


class Error(Exception):
    pass


if __name__ == '__main__':
    main()
