import getpass

import yaml
from ansible.parsing.vault import AnsibleVaultError
from ansible_vault import Vault
from memoized import memoized, memoized_property

from commcare_cloud.environment.constants import constants
from commcare_cloud.environment.paths import DefaultPaths, get_role_defaults
from commcare_cloud.environment.schemas.app_processes import AppProcessesConfig

from ansible.inventory.manager import InventoryManager
from ansible.parsing.dataloader import DataLoader
from ansible.vars.manager import VariableManager

from commcare_cloud.environment.schemas.fab_settings import FabSettingsConfig
from commcare_cloud.environment.schemas.meta import MetaConfig
from commcare_cloud.environment.schemas.postgresql import PostgresqlConfig
from commcare_cloud.environment.schemas.proxy import ProxyConfig
from commcare_cloud.environment.users import UsersConfig


class Environment(object):
    def __init__(self, paths):
        self.paths = paths

    def check(self):

        included_disallowed_public_variables = set(self.public_vars.keys()) & self._disallowed_public_variables
        assert not included_disallowed_public_variables, \
            "Disallowed variables in {}: {}".format(self.paths.public_yml, included_disallowed_public_variables)
        self.meta_config
        self.users_config
        self.raw_app_processes_config
        self.app_processes_config
        self.fab_settings_config
        self.inventory_manager
        self.postgresql_config
        self.proxy_config
        self.create_generated_yml()

    @memoized
    def get_ansible_vault_password(self):
        return getpass.getpass("Vault Password: ")

    @memoized
    def get_vault_variables(self):
        # try unencrypted first for tests
        with open(self.paths.vault_yml, 'r') as f:
            vault_vars = yaml.load(f)
        if isinstance(vault_vars, dict):
            return vault_vars

        while True:
            try:
                vault = Vault(self.get_ansible_vault_password())
                with open(self.paths.vault_yml, 'r') as vf:
                    return vault.load(vf.read())
            except AnsibleVaultError:
                print('incorrect password')
                self.get_ansible_vault_password.reset_cache(self)

    def get_vault_var(self, var):
        path = var.split('.')
        context = self.get_vault_variables()
        for node in path:
            context = context[node]
        return context

    def get_ansible_user_password(self):
        return self.get_vault_variables()['ansible_sudo_pass']

    @memoized_property
    def public_vars(self):
        """contents of public.yml, as a dict"""
        with open(self.paths.public_yml) as f:
            return yaml.load(f)

    @memoized_property
    def _disallowed_public_variables(self):
        return set(get_role_defaults('postgresql').keys()) | set(ProxyConfig.get_claimed_variables())

    @memoized_property
    def meta_config(self):
        with open(self.paths.meta_yml) as f:
            meta_json = yaml.load(f)
        return MetaConfig.wrap(meta_json)

    @memoized_property
    def postgresql_config(self):
        with open(self.paths.postgresql_yml) as f:
            postgresql_json = yaml.load(f)
        postgresql_config = PostgresqlConfig.wrap(postgresql_json)
        postgresql_config.replace_hosts(self)
        postgresql_config.check()
        return postgresql_config

    @memoized_property
    def proxy_config(self):
        with open(self.paths.proxy_yml) as f:
            proxy_json = yaml.load(f)
        proxy_config = ProxyConfig.wrap(proxy_json)
        proxy_config.check()
        return proxy_config

    @memoized_property
    def users_config(self):
        with open(self.paths.get_users_yml(self.meta_config.users)) as f:
            users_json = yaml.load(f)
        return UsersConfig.wrap(users_json)

    @memoized_property
    def raw_app_processes_config(self):
        """
        collated contents of app-processes.yml files, as an AppProcessesConfig object

        includes environmental-defaults/app-processes.yml as well as <env>/app-processes.yml
        """
        with open(self.paths.app_processes_yml_default) as f:
            app_processes_json = yaml.load(f)
        with open(self.paths.app_processes_yml) as f:
            app_processes_json.update(yaml.load(f))

        raw_app_processes_config = AppProcessesConfig.wrap(app_processes_json)
        raw_app_processes_config.check()
        return raw_app_processes_config

    @memoized_property
    def app_processes_config(self):
        app_processes_config = AppProcessesConfig.wrap(self.raw_app_processes_config.to_json())
        app_processes_config.check_and_translate_hosts(self)
        app_processes_config.check()
        return app_processes_config

    @memoized_property
    def fab_settings_config(self):
        """
        collated contents of fab-settings.yml files, as a FabSettingsConfig object

        includes environmental-defaults/fab-settings.yml as well as <env>/fab-settings.yml
        """
        with open(self.paths.fab_settings_yml_default) as f:
            fab_settings_json = yaml.load(f)
        with open(self.paths.fab_settings_yml) as f:
            fab_settings_json.update(yaml.load(f) or {})

        fab_settings_config = FabSettingsConfig.wrap(fab_settings_json)
        return fab_settings_config

    @memoized_property
    def _ansible_inventory_data_loader(self):
        return DataLoader()

    @memoized_property
    def inventory_manager(self):
        return InventoryManager(loader=self._ansible_inventory_data_loader,
                                sources=self.paths.inventory_ini)

    @memoized_property
    def groups(self):
        """
        mimics ansible's `groups` variable

        env.groups['postgresql'][0] => {{ groups.postgresql.0 }}
        """
        return {group: [
            host for host in hosts
        ] for group, hosts in self.inventory_manager.get_groups_dict().items()}

    @memoized_property
    def sshable_hostnames_by_group(self):
        """
        filename is a path to an ansible inventory file

        returns a mapping of group names ("webworker", "proxy", etc.)
        to lists of hostnames as listed in the inventory file.
        ("Hostnames" can also be IP addresses.)
        If the hostname in the file includes :<port>, that will be included here as well.

        """
        inventory = self.inventory_manager
        var_manager = VariableManager(self._ansible_inventory_data_loader, inventory)
        # use the ip address specified by ansible_host to ssh in if it's given
        ssh_addr_map = {
            host.name: var_manager.get_vars(host=host).get('ansible_host', host.name)
            for host in inventory.get_hosts()}
        # use the port specified by ansible_port to ssh in if it's given
        port_map = {host.name: var_manager.get_vars(host=host).get('ansible_port')
                    for host in inventory.get_hosts()}
        return {group: [
            '{}:{}'.format(ssh_addr_map[host], port_map[host])
            if port_map[host] is not None else ssh_addr_map[host]
            for host in hosts
        ] for group, hosts in self.inventory_manager.get_groups_dict().items()}

    @memoized_property
    def hostname_map(self):
        """Mapping of inventory hostname (IP) to assigned hostname"""
        mapping = {}
        for host in self.inventory_manager.hosts.values():
            if 'hostname' in host.vars:
                mapping[host.name] = host.vars['hostname']
            for group in host.groups:
                if len(group.hosts) == 1 and 'hostname' in group.vars:
                    mapping[host.name] = group.vars['hostname']

        return mapping

    def _run_last_minute_checks(self):
        assert len(self.groups.get('rabbitmq', [])) == 1, \
            "You must have exactly one host in the [rabbitmq] group"
        assert len(self.groups.get('redis', [])) == 1, \
            "You must have exactly one host in the [redis] group"

    def create_generated_yml(self):
        self._run_last_minute_checks()
        generated_variables = {
            'deploy_env': self.meta_config.deploy_env,
            'env_monitoring_id': self.meta_config.env_monitoring_id,
            'dev_users': self.users_config.dev_users.to_json(),
            'authorized_keys_dir': '{}/'.format(self.paths.authorized_keys_dir),
            'known_hosts_file': self.paths.known_hosts,
        }
        generated_variables.update(self.app_processes_config.to_generated_variables())
        generated_variables.update(self.postgresql_config.to_generated_variables())
        generated_variables.update(self.proxy_config.to_generated_variables())
        generated_variables.update(constants.to_json())

        with open(self.paths.generated_yml, 'w') as f:
            f.write(yaml.safe_dump(generated_variables))

    def translate_host(self, host, filename_for_error):
        if host == 'None' or host in self.inventory_manager.hosts:
            return host
        else:
            group = self.groups.get(host)
            assert group, 'Unknown host referenced in {}: {}'.format(filename_for_error, host)
            assert len(group) == 1, (
                'Unable to translate host referenced '
                'in {} to a single host name: {}'.format(filename_for_error, host))
            return group[0]

    def get_hostname(self, inventory_host, full=True):
        hostname = self.hostname_map.get(inventory_host)
        if not hostname:
            return inventory_host
        if full and 'internal_domain_name' in self.public_vars:
            return "{}.{}".format(hostname, self.public_vars['internal_domain_name'])
        return hostname



@memoized
def get_environment(env_name):
    return Environment(DefaultPaths(env_name))
