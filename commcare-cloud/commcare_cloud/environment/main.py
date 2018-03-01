import yaml
from memoized import memoized

from commcare_cloud.environment.paths import DefaultPaths, memoized_property
from commcare_cloud.environment.schemas.app_processes import AppProcessesConfig

from ansible.inventory.manager import InventoryManager
from ansible.parsing.dataloader import DataLoader
from ansible.vars.manager import VariableManager


class Environment(object):
    def __init__(self, paths):
        self.paths = paths

    @memoized_property
    def public_vars(self):
        """contents of public.yml, as a dict"""
        with open(self.paths.public_yml) as f:
            return yaml.load(f)

    @memoized_property
    def app_processes_config(self):
        """
        collated contents of app-processes.yml files, as an AppProcessesConfig object

        includes environmental-defaults/app-processes.yml as well as <env>/app-processes.yml
        """
        with open(self.paths.app_processes_yml_default) as f:
            app_processes_json = yaml.load(f)
        with open(self.paths.app_processes_yml) as f:
            app_processes_json.update(yaml.load(f))

        app_processes_config = AppProcessesConfig.wrap(app_processes_json)
        app_processes_config.check()
        return app_processes_config

    @memoized_property
    def translated_app_processes_config(self):
        app_processes_config = AppProcessesConfig.wrap(self.app_processes_config.to_json())
        app_processes_config.check_and_translate_hosts(self)
        app_processes_config.check()
        return app_processes_config

    @memoized_property
    def _ansible_inventory_data_loader(self):
        return DataLoader()

    @memoized_property
    def inventory_manager(self):
        return InventoryManager(loader=self._ansible_inventory_data_loader,
                                sources=self.paths.inventory_ini)

    @memoized_property
    def inventory_hosts_by_group(self):
        """
        filename is a path to an ansible inventory file

        returns a mapping of group names ("webworker", "proxy", etc.)
        to lists of hostnames as listed in the inventory file.
        ("Hostnames" can also be IP addresses.)
        If the hostname in the file includes :<port>, that will be included here as well.

        """
        inventory = self.inventory_manager
        var_manager = VariableManager(self._ansible_inventory_data_loader, inventory)
        port_map = {host.name: var_manager.get_vars(host=host).get('ansible_port')
                    for host in inventory.get_hosts()}
        return {group: [
            '{}:{}'.format(host, port_map[host])
            if port_map[host] is not None else host
            for host in hosts
        ] for group, hosts in self.inventory_manager.get_groups_dict().items()}


@memoized
def get_environment(env_name):
    return Environment(DefaultPaths(env_name))
