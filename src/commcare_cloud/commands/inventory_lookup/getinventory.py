"""
Utilities to get server hostname or IP address from an inventory file and group.
"""
import re
from collections import defaultdict

import attr
from ansible.utils.display import Display

from commcare_cloud.environment.main import get_environment

display = Display()


class HostMatchException(Exception):
    pass


@attr.s
class HostPattern(object):
    user = attr.ib()
    group = attr.ib()
    index = attr.ib()


def get_instance_group(environment, group, add_groups=False):
    env = get_environment(environment)
    names = env.sshable_hostnames_by_group[group]
    if add_groups:
        names = _add_groups(names, env)
    return names


def _add_groups(names, env):
    """Add groups to hostnames and sort result by groups"""
    def format_host(name):
        return "{name} - {other_names}".format(
            name=name,
            other_names=", ".join(sorted(
                groups_by_host[name],
                key=lambda g: len(hosts_by_group[g])
            ))
        )
    hosts_by_group = env.sshable_hostnames_by_group
    groups_by_host = defaultdict(list)
    for group, hosts in hosts_by_group.items():
        for host in hosts:
            groups_by_host[host].append(group)
    result = [format_host(n) for n in names]
    return sorted(result, key=lambda n: n.split(" - ", 1)[-1])


def split_host_group(group):
    ansible_style_pattern = re.match(r'^(?P<user>(.*?)@)?(?P<group>.*?)(\[(?P<index>\d+)\])?$', group)
    if ansible_style_pattern:
        user = ansible_style_pattern.group('user')
        group = ansible_style_pattern.group('group')
        index = ansible_style_pattern.group('index')
        return HostPattern(user, group, int(index) if index else None)
    return HostPattern(None, group, None)


def get_server_address(environment, group, allow_multiple=False):
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
        username = ""

    if re.match(r'(\d+\.?){4}', group):
        # short circuit for IP addresses
        return username + group

    try:
        servers = get_instance_group(environment, group, add_groups=allow_multiple)
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
            if allow_multiple:
                return "\n".join(username + s for s in servers)
            raise HostMatchException(
                "There are {num} servers in the '{group}' group\n"
                "Please specify the index of the server. Example: {group}[0]\n"
                .format(num=len(servers), group=group)
            )
        server = servers[index]
    else:
        server = servers[index or 0]

    return username + server
