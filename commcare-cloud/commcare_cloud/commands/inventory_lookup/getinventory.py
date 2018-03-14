"""
Utilities to get server hostname or IP address from an inventory file and group.
"""
from __future__ import print_function
from __future__ import absolute_import
import sys

from commcare_cloud.environment.main import get_environment


def get_instance_group(environment, group):
    env = get_environment(environment)
    return env.inventory_hosts_by_group[group]


def get_monolith_address(environment, exit=sys.exit):
    env = get_environment(environment)
    hosts = env.inventory_manager.get_hosts()
    if len(hosts) != 1:
        exit("There are {} servers in the environment. Please include the 'server'"
             "argument to select one.".format(len(hosts)))
    else:
        return hosts[0].address


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
