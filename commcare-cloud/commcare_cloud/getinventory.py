"""
Utilities to get server hostname or IP address from an inventory file and group.
"""
from __future__ import print_function
from __future__ import absolute_import
import os
import sys

from .paths import FAB_DIR, get_inventory_filepath


def import_read_inventory_file():
    """
    This is a hack that makes this script dependent on commcarehq-ansible/fab

    Not sure this is a great idea. If you ever find its brittleness breaks something,
    feel free to copy and paste read_inventory_file from there, which is how it was before.
    """
    sys.path.append(FAB_DIR)
    from fab.utils import read_inventory_file
    sys.path.remove(FAB_DIR)
    return read_inventory_file


def get_instance_group(instance, group):
    read_inventory_file = import_read_inventory_file()
    servers = read_inventory_file(instance)
    return servers[group]


def get_server_address(environment, group, exit=sys.exit):
    if "@" in group:
        username, group = group.split('@', 1)
        username += "@"
    else:
        username = ""
    if ':' in group:
        group, index = group.rsplit(':', 1)
        try:
            index = int(index)
        except (TypeError, ValueError):
            exit("Non-numeric group index: {}".format(index))
    else:
        index = None

    try:
        servers = get_instance_group(environment, group)
    except IOError as err:
        exit(err)
    except KeyError as err:
        exit("Unknown server name/group: {}\n".format(group))

    if index is not None and index > len(servers) - 1:
        exit(
            "Invalid group index: {index}\n"
            "Please specify a number between 0 and {max} inclusive\n"
            .format(index=index, max=len(servers) - 1)
        )
    if len(servers) > 1:
        if index is None:
            exit(
                "There are {num} servers in the '{group}' group\n"
                "Please specify the index of the server. Example: {group}:0\n"
                .format(num=len(servers), group=group)
            )
        server = servers[index]
    else:
        server = servers[index or 0]

    return username + server
