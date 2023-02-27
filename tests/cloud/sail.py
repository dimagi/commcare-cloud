#! /usr/bin/env python
"""
Run test servers with podman-compose.

Commands:
    up - start the containers and optionally generate an inventory file.
    down - destroy containers.
    rebuild - efficiently rebuild podman images.
    COMPOSE_COMMAND - arbitrary compose command.

Usage:
    sail.py up [-- OPTIONS ...]
    sail.py down
    sail.py rebuild
    sail.py COMPOSE_COMMAND [-- OPTIONS ...]

Environment variables:
    TEST_CLOUD_AUTHORIZED_KEYS: Path to ssh authorized_keys file for the admin
        user in containers. Defaults to '~/.ssh/id_rsa.pub'
    TEST_CLOUD_CONTAINER_CONTEXT: Path to directory containing a Dockerfile to
        use instead of the default one in the same directory as this script.
    TEST_CLOUD_SHARED_DIR: Optional directory path to be mounted at /mnt in
        worker containers. A shared volume named 'test_cloud_shared' will be
        used if not set.
    TEST_CLOUD_WORKERS: The number of worker containers to create. Default: 1
"""
import os
import sys
from pathlib import Path

import sh
from docopt import docopt


def main():
    arguments = docopt(__doc__)
    os.environ.setdefault(
        "TEST_CLOUD_AUTHORIZED_KEYS", os.path.expanduser("~/.ssh/id_rsa.pub"))
    if arguments["up"]:
        up(opts=arguments.get("OPTIONS") or [])
    elif arguments["down"]:
        down()
    elif arguments["rebuild"]:
        rebuild()
    elif arguments["COMPOSE_COMMAND"]:
        opts = arguments.get("OPTIONS") or []
        compose(arguments["COMPOSE_COMMAND"], *opts)
    else:
        raise ValueError(arguments)


def up(opts=()):
    args = _context()
    sh.podman_compose("up", "-d", *opts, **args)
    return 2222


def down():
    """Destroy running containers"""
    sh.podman_compose("down", **_context())


def rebuild():
    down()
    _remove_image("localhost/cloud_portal")
    sh.podman_compose("build", "portal", **_context())
    _remove_image("localhost/cloud_worker")
    sh.podman_compose("build", "worker", **_context())


def compose(command, *opts):
    sh.podman_compose(command, *opts, **_context())


def _remove_image(name):
    context = _context()
    context.pop("_err")
    try:
        sh.podman("rmi", name, **context)
    except sh.ErrorReturnCode as err:
        if b"image not known" in err.stderr:
            return
        raise


def _context():
    return {
        "_cwd": Path(__file__).parent,
        "_out": sys.stdout,
        "_err": sys.stdout,
    }


if __name__ == "__main__":
    main()
