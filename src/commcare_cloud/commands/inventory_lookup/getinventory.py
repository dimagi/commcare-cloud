"""
Utilities to get server hostname or IP address from an inventory file and group.
"""
from __future__ import absolute_import, print_function

from __future__ import unicode_literals
import re

import attr
from ansible.utils.display import Display

from commcare_cloud.commands.terraform.aws import get_default_username
from commcare_cloud.environment.main import get_environment

display = Display()


class HostMatchException(Exception):
    pass


@attr.s
class HostPattern(object):
    user = attr.ib()
    group = attr.ib()
    index = attr.ib()


def get_instance_group(environment, group):
    env = get_environment(environment)
    return env.sshable_hostnames_by_group[group]


def get_monolith_address(environment):
    env = get_environment(environment)
    hosts = env.inventory_manager.get_hosts()
    if len(hosts) != 1:
        raise HostMatchException("There are {} servers in the environment. Please include the 'server'"
             "argument to select one.".format(len(hosts)))
    else:
        return get_server_address(environment, 'all')


def split_host_group(group):
    ansible_style_pattern = re.match(r'^(?P<user>(.*?)@)?(?P<group>.*?)(\[(?P<index>\d+)\])?$', group)
    if ansible_style_pattern:
        user = ansible_style_pattern.group('user')
        group = ansible_style_pattern.group('group')
        index = ansible_style_pattern.group('index')
        return HostPattern(user, group, int(index) if index else None)
    return HostPattern(None, group, None)


def get_server_address(environment, group):
    host_group = split_host_group(group)
    username, group, index = host_group.user, host_group.group, host_group.index

    if ':' in group:
        display.warning("Use '[x]' to select hosts instead of ':x' which has been deprecated.")
        group, index = group.rsplit(':', 1)
        try:
            index = int(index)
        except (TypeError, ValueError):
            raise HostMatchException("Non-numeric group index: {}".format(index))

    if not username:
        default_username = get_default_username()
        if default_username.is_guess:
            username = ""
        else:
            username = "{}@".format(default_username)

    if re.match(r'(\d+\.?){4}', group):
        # short circuit for IP addresses
        return username + group

    try:
        servers = get_instance_group(environment, group)
    except IOError as err:
        raise HostMatchException(err)
    except KeyError:
        raise HostMatchException("Unknown server name/group: {}\n".format(group))

    if index is not None and index > len(servers) - 1:
        raise HostMatchException(
            "Invalid group index: {index}\n"
            "Please specify a number between 0 and {max} inclusive\n"
            .format(index=index, max=len(servers) - 1)
        )
    if len(servers) > 1:
        if index is None:
            raise HostMatchException(
                "There are {num} servers in the '{group}' group\n"
                "Please specify the index of the server. Example: {group}:0\n"
                .format(num=len(servers), group=group)
            )
        server = servers[index]
    else:
        server = servers[index or 0]

    return username + server
