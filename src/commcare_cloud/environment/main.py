from __future__ import absolute_import, unicode_literals

import os
import re
from collections import Counter
from datetime import datetime
from io import open

import yaml
from ansible.inventory.manager import InventoryManager
from ansible.parsing.dataloader import DataLoader
from ansible.parsing.utils.yaml import from_yaml
from ansible.vars.manager import VariableManager
from memoized import memoized, memoized_property
from six.moves import map

from commcare_cloud.environment.constants import constants
from commcare_cloud.environment.exceptions import EnvironmentException
from commcare_cloud.environment.paths import DefaultPaths, get_role_defaults

from commcare_cloud.environment.remote import RemoteConf
from commcare_cloud.environment.schemas.app_processes import AppProcessesConfig
from commcare_cloud.environment.schemas.aws import AwsConfig
from commcare_cloud.environment.schemas.elasticsearch import (
    ElasticsearchConfig,
)
from commcare_cloud.environment.schemas.fab_settings import FabSettingsConfig
from commcare_cloud.environment.schemas.meta import MetaConfig
from commcare_cloud.environment.schemas.postgresql import PostgresqlConfig
from commcare_cloud.environment.schemas.prometheus import PrometheusConfig
from commcare_cloud.environment.schemas.proxy import ProxyConfig
from commcare_cloud.environment.schemas.terraform import TerraformConfig
from commcare_cloud.environment.users import UsersConfig
from commcare_cloud.yaml import PreserveUnsafeDumper


class Environment(object):
    def __init__(self, paths):
        self.paths = paths

    @property
    def name(self):
        return self.paths.env_name

    @memoized_property
    def remote_conf(self):
        return RemoteConf(self)

    def __repr__(self):
        return "Environment(name={})".format(self.name)

    def check(self):

        included_disallowed_public_variables = set(self.public_vars.keys()) & self._disallowed_public_variables
        assert not included_disallowed_public_variables, \
            "Disallowed variables in {}: {}".format(self.paths.public_yml, included_disallowed_public_variables)
        self.check_known_hosts()
        self.meta_config
        self.users_config
        self.inventory_manager
        if not self.meta_config.bare_non_cchq_environment:
            self.app_processes_config
            self.fab_settings_config
            self.postgresql_config
            self.proxy_config
        self.create_generated_yml()

    def check_known_hosts(self):
        if not os.path.exists(self.paths.known_hosts):
            return
        blacklist = set(self.groups.get('ansible_skip', []))
        hostname_to_sshable = {
            inventory_hostname: sshable.split(':')[0]
            for sshable, inventory_hostname in self.inventory_hostname_map.items()
        }
        inventory_hostnames = {
            host for hosts in self.groups.values()
            for host in hosts if host not in blacklist
        }
        expected_hosts = {
            (hostname_to_sshable[host], self.hostname_map.get(host))
            for host in inventory_hostnames
        }
        with open(self.paths.known_hosts, encoding='utf-8') as f:
            known_hosts_contents = f.read()
        missing_hosts = {
            (sshable, hostname) for sshable, hostname in expected_hosts
            if not re.search(r'\b{}\b'.format(sshable), known_hosts_contents)
        }
        if missing_hosts:
            raise EnvironmentException(
                'The following hosts are missing from known_hosts:\n{}'.format(
                   '\n'.join(
                       "{} ({})".format(sshable, hostname) for sshable, hostname in missing_hosts
                   )
                )
            )

    def get_secret(self, var):
        return self.secrets_backend.get_secret(var)

    @memoized_property
    def secrets_backend(self):
        return self.meta_config.get_secrets_backend_class().from_environment(self)

    def get_ansible_user_password(self):
        return self.get_secret('ansible_sudo_pass')

    @memoized_property
    def public_vars(self):
        try:
            """contents of public.yml, as a dict"""
            with open(self.paths.public_yml, encoding='utf-8') as f:
                return from_yaml(f)
        except FileNotFoundError:
            return {}

    @property
    def python_version(self):
        return self.public_vars.get('python_version', '3.6')

    @memoized_property
    def _disallowed_public_variables(self):
        return set(get_role_defaults('postgresql_base').keys()) | \
               set(get_role_defaults('pgbouncer').keys()) | \
               set(ProxyConfig.get_claimed_variables())

    @memoized_property
    def meta_config(self):
        with open(self.paths.meta_yml, encoding='utf-8') as f:
            meta_json = from_yaml(f)
        return MetaConfig.wrap(meta_json)

    @memoized_property
    def postgresql_config(self):
        with open(self.paths.postgresql_yml, encoding='utf-8') as f:
            postgresql_json = from_yaml(f)
        postgresql_config = PostgresqlConfig.wrap(postgresql_json)
        postgresql_config.replace_hosts(self)
        postgresql_config.check()
        return postgresql_config

    @memoized_property
    def elasticsearch_config(self):
        try:
            with open(self.paths.elasticsearch_yml, encoding='utf-8') as f:
                elasticsearch_json = from_yaml(f)
        except IOError:
            # It's fine to omit this file
            elasticsearch_json = {}
        number_of_replicas = 0 if len(self.groups['elasticsearch']) < 2 else 1
        elasticsearch_config = ElasticsearchConfig.wrap(elasticsearch_json)
        if elasticsearch_config.settings.default.number_of_replicas is None:
            elasticsearch_config.settings.default.number_of_replicas = number_of_replicas
        return elasticsearch_config

    @memoized_property
    def proxy_config(self):
        with open(self.paths.proxy_yml, encoding='utf-8') as f:
            proxy_json = from_yaml(f)
        proxy_config = ProxyConfig.wrap(proxy_json)
        proxy_config.check()
        return proxy_config

    @memoized_property
    def prometheus_config(self):
        try:
            with open(self.paths.prometheus_yml, encoding='utf-8') as f:
                prometheus_json = from_yaml(f)
        except IOError:
            return None
        return PrometheusConfig.wrap(prometheus_json)

    @memoized_property
    def users_config(self):
        user_groups_from_yml = self.meta_config.users
        absent_users = []
        present_users = []
        for user_group_from_yml in user_groups_from_yml:
            with open(self.paths.get_users_yml(user_group_from_yml), encoding='utf-8') as f:
                user_group_json = from_yaml(f)
            present_users += user_group_json['dev_users']['present']
            absent_users += user_group_json['dev_users']['absent']
        self.check_user_group_absent_present_overlaps(absent_users, present_users)
        all_users_json = {'dev_users': {'absent': absent_users, 'present': present_users}}
        return UsersConfig.wrap(all_users_json)

    @memoized_property
    def terraform_config(self):
        try:
            with open(self.paths.terraform_yml, encoding='utf-8') as f:
                config_yml = from_yaml(f)
        except IOError:
            return None
        config_yml['environment'] = config_yml.get('environment', self.meta_config.env_monitoring_id)
        return TerraformConfig.wrap(config_yml)

    @memoized_property
    def aws_config(self):
        try:
            with open(self.paths.aws_yml, encoding='utf-8') as f:
                config_yml = from_yaml(f)
        except IOError:
            config_yml = {}
        return AwsConfig.wrap(config_yml)

    def get_authorized_key(self, user):
        with open(self.paths.get_authorized_key_file(user), encoding='utf-8') as f:
            return f.read()

    def check_user_group_absent_present_overlaps(self, absent_users, present_users):
        if not set(present_users).isdisjoint(absent_users):
            repeated_users = list((Counter(present_users) & Counter(absent_users)).elements())
            raise EnvironmentException('The user(s) {} appear(s) in both the absent and present users list for '
                                       'the environment {}. Please fix this and try again.'.format((', '.join(
                                        map(str, repeated_users))), self.meta_config.deploy_env))

    @memoized_property
    def _raw_app_processes_config(self):
        """
        collated contents of app-processes.yml files, as an AppProcessesConfig object

        includes environmental-defaults/app-processes.yml as well as <env>/app-processes.yml
        """
        with open(self.paths.app_processes_yml_default, encoding='utf-8') as f:
            app_processes_json = from_yaml(f)
        with open(self.paths.app_processes_yml, encoding='utf-8') as f:
            app_processes_json.update(from_yaml(f))

        raw_app_processes_config = AppProcessesConfig.wrap(app_processes_json)
        raw_app_processes_config.check()
        return raw_app_processes_config

    @memoized_property
    def app_processes_config(self):
        app_processes_config = AppProcessesConfig.wrap(self._raw_app_processes_config.to_json())
        app_processes_config.check_and_translate_hosts(self)
        app_processes_config.check()
        return app_processes_config

    @memoized_property
    def fab_settings_config(self):
        """
        collated contents of fab-settings.yml files, as a FabSettingsConfig object

        includes environmental-defaults/fab-settings.yml as well as <env>/fab-settings.yml
        """
        with open(self.paths.fab_settings_yml_default, encoding='utf-8') as f:
            fab_settings_json = from_yaml(f)
        with open(self.paths.fab_settings_yml, encoding='utf-8') as f:
            fab_settings_json.update(from_yaml(f) or {})

        fab_settings_config = FabSettingsConfig.wrap(fab_settings_json)
        return fab_settings_config

    @memoized_property
    def _ansible_inventory_data_loader(self):
        return DataLoader()

    @memoized_property
    def inventory_manager(self):
        return InventoryManager(
            loader=self._ansible_inventory_data_loader,
            sources=self.paths.inventory_source
        )

    @property
    def _ansible_inventory_variable_manager(self):
        return get_variable_manager(self._ansible_inventory_data_loader, self.inventory_manager)

    def get_host_vars(self, host):
        host_object, = [h for h in self.inventory_manager.get_hosts(ignore_limits=True) if h.name == host]
        return self._ansible_inventory_variable_manager.get_vars(host=host_object)

    @memoized_property
    def groups(self):
        """
        mimics ansible's `groups` variable

        env.groups['postgresql'][0] => {{ groups.postgresql.0 }}
        """
        return {group: [
            host for host in hosts
        ] for group, hosts in self.inventory_manager.get_groups_dict().items()}

    @staticmethod
    def format_sshable_host(ansible_host, ansible_port):
        if ansible_port is None:
            return ansible_host
        else:
            return '{}:{}'.format(ansible_host, ansible_port)

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
        var_manager = self._ansible_inventory_variable_manager
        # use the ip address specified by ansible_host to ssh in if it's given
        ssh_addr_map = {
            host.name: var_manager.get_vars(host=host).get('ansible_host', host.name)
            for host in inventory.get_hosts(ignore_limits=True)}
        # use the port specified by ansible_port to ssh in if it's given
        port_map = {host.name: var_manager.get_vars(host=host).get('ansible_port')
                    for host in inventory.get_hosts(ignore_limits=True)}
        return {group: [
            self.format_sshable_host(ssh_addr_map[host], port_map[host])
            for host in hosts
        ] for group, hosts in self.inventory_manager.get_groups_dict().items()}

    @memoized_property
    def inventory_hostname_map(self):
        """
        sshable hostname (including optional port) => inventory_hostname

        in the common case, sshable hostname _is_ inventory_hostname, but if you have
        the optional ansible_port or ansible_host set, then it will be different,
        and the same format as used in sshable_hostnames_by_group
        """
        var_manager = self._ansible_inventory_variable_manager

        mapping = {}
        for host in self.inventory_manager.get_hosts():
            ansible_port = var_manager.get_vars(host=host).get('ansible_port')
            ansible_host = var_manager.get_vars(host=host).get('ansible_host', host.name)
            mapping[self.format_sshable_host(ansible_host, ansible_port)] = host.name
        return mapping

    @memoized_property
    def hostname_map(self):
        """Mapping of inventory hostname (IP) to assigned hostname"""
        mapping = {}
        for host in self.inventory_manager.hosts.values():
            if 'alt_hostname' in host.vars:
                mapping[host.name] = host.vars['alt_hostname']
            elif 'hostname' in host.vars:
                mapping[host.name] = host.vars['hostname']
            for group in host.groups:
                if len(group.hosts) == 1 and 'hostname' in group.vars:
                    mapping[host.name] = group.vars['hostname']

        return mapping

    def create_generated_yml(self):
        generated_variables = {
            'deploy_env': self.meta_config.deploy_env,
            'env_monitoring_id': self.meta_config.env_monitoring_id,
            'dev_users': self.users_config.dev_users.to_json(),
            'authorized_keys_dir': '{}/'.format(os.path.realpath(self.paths.authorized_keys_dir)),
            'known_hosts_file': self.paths.known_hosts,
            'env_files_dir': self.paths.files_dir,
            'commcarehq_repository': (
                self.fab_settings_config.code_repo
                if not self.meta_config.bare_non_cchq_environment else {}
            ),
            'ES_SETTINGS': (
                self.elasticsearch_config.settings.to_json()
                if not self.meta_config.bare_non_cchq_environment else {}
            ),
            'new_release_name': self.new_release_name(),
            'git_repositories': [repo.to_generated_variables() for repo in self.meta_config.git_repositories],
            'deploy_keys': dict(self.meta_config.deploy_keys.items()),
        }
        if not self.meta_config.bare_non_cchq_environment:
            generated_variables.update(self.app_processes_config.to_generated_variables())
            generated_variables.update(self.postgresql_config.to_generated_variables(self))
            generated_variables.update(self.proxy_config.to_generated_variables())
            if self.prometheus_config:
                generated_variables.update(self.prometheus_config.to_generated_variables())

        generated_variables.update(constants.to_json())

        if os.path.exists(self.paths.dimagi_key_store_vault):
            generated_variables.update({'keystore_file': self.paths.dimagi_key_store_vault})

        generated_variables.update(self.secrets_backend.get_generated_variables())

        with open(self.paths.generated_yml, 'w', encoding='utf-8') as f:
            f.write(yaml.dump(generated_variables, Dumper=PreserveUnsafeDumper))

    @memoized
    def new_release_name(self):
        from commcare_cloud.fab.const import DATE_FMT
        return datetime.utcnow().strftime(DATE_FMT)

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

    def get_hostname(self, sshable_hostname, full=True):
        hostname = self.hostname_map.get(self.inventory_hostname_map[sshable_hostname])
        if not hostname:
            return sshable_hostname
        if full and self.public_vars.get('internal_domain_name'):
            return "{}.{}".format(hostname, self.public_vars['internal_domain_name'])
        return hostname


@memoized
def get_environment(env_name):
    return Environment(DefaultPaths(env_name))


@memoized
def get_variable_manager(data_loader, inventory_manager):
    return VariableManager(data_loader, inventory_manager)
