from ansible.inventory.manager import InventoryManager
from ansible.parsing.dataloader import DataLoader
from ansible.vars.manager import VariableManager

from commcare_cloud.environment.paths import get_inventory_filepath


def get_inventory(env_name, data_loader=None):
    data_loader = data_loader or DataLoader()
    return InventoryManager(loader=data_loader, sources=get_inventory_filepath(env_name))


def read_inventory_file(env_name):
    """
    filename is a path to an ansible inventory file

    returns a mapping of group names ("webworker", "proxy", etc.)
    to lists of hostnames as listed in the inventory file.
    ("Hostnames" can also be IP addresses.)
    If the hostname in the file includes :<port>, that will be included here as well.

    """
    data_loader = DataLoader()
    inventory = get_inventory(env_name, data_loader=data_loader)
    var_manager = VariableManager(data_loader, inventory)
    port_map = {host.name: var_manager.get_vars(host=host).get('ansible_port')
                for host in inventory.get_hosts()}
    return {group: [
        '{}:{}'.format(host, port_map[host])
        if port_map[host] is not None else host
        for host in hosts
    ] for group, hosts in get_inventory(env_name).get_groups_dict().items()}
