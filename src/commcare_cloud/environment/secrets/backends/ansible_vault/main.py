from __future__ import absolute_import, print_function, unicode_literals

import getpass
import os
import sys
from contextlib import contextmanager
from io import open

import datadog.api
import yaml
from ansible.parsing.vault import AnsibleVaultError
from ansible_vault import Vault
from memoized import memoized
from six.moves import shlex_quote

from commcare_cloud.environment.paths import ANSIBLE_DIR
from commcare_cloud.environment.secrets.backends.abstract_backend import (
    AbstractSecretsBackend,
)
from commcare_cloud.environment.secrets.secrets_schema import (
    get_generated_variables,
    get_known_secret_specs_by_name,
)


class AnsibleVaultSecretsBackend(AbstractSecretsBackend):
    name = 'ansible-vault'

    def __init__(self, env_name, vault_file_path, record_to_datadog=False, ask_vault_pass=True):
        self.env_name = env_name
        self.vault_file_path = vault_file_path
        self.record_to_datadog = record_to_datadog
        self.should_send_vault_loaded_event = True
        self.ask_vault_pass = ask_vault_pass

    @classmethod
    def from_environment(cls, environment):
        try:
            datadog_enabled = environment.public_vars.get('DATADOG_ENABLED')
        except IOError:
            # some test envs don't have public.yml
            datadog_enabled = False

        try:
            commcare_cloud_use_vault = environment.public_vars.get('commcare_cloud_use_vault', True)
        except IOError:
            commcare_cloud_use_vault = True

        return cls(
            environment.name, environment.paths.vault_yml,
            record_to_datadog=datadog_enabled,
            ask_vault_pass=commcare_cloud_use_vault,
        )

    def prompt_user_input(self):
        # call this for its side-effect: asking the user for the vault password
        # (and thus not requiring that thereafter)
        self._get_ansible_vault_password_and_record()

    def get_extra_ansible_args(self):
        extra_ansible_args = ('-e', '@{}'.format(self.vault_file_path))
        if self.ask_vault_pass:
            extra_ansible_args += (
                '--vault-password-file={}/echo_vault_password.sh'.format(ANSIBLE_DIR),
            )
        return extra_ansible_args

    def get_extra_ansible_env_vars(self):
        if self.ask_vault_pass:
            return {
                'ANSIBLE_VAULT_PASSWORD': self._get_ansible_vault_password_and_record(),
            }
        else:
            return {}

    @staticmethod
    def get_generated_variables():
        return get_generated_variables(lambda secret_spec: secret_spec.get_legacy_reference())

    def _get_ansible_vault_password_and_record(self):
        """Get ansible vault password

        This method has a side-effect: it records a Datadog event with
        the commcare-cloud command that is currently being run.
        """
        self._get_vault_variables_and_record()
        return self._get_ansible_vault_password()

    @memoized
    def _get_vault_variables_and_record(self):
        """Get ansible vault variables

        This method has a side-effect: it records a Datadog event with
        the commcare-cloud command that is currently being run.
        """
        vault_vars = self._get_vault_variables()
        if "secrets" in vault_vars:
            self._record_vault_loaded_event(vault_vars["secrets"])
        return vault_vars

    @memoized
    def _get_ansible_vault_password(self):
        return (
            os.environ.get('ANSIBLE_VAULT_PASSWORD') or
            getpass.getpass("Vault Password for '{}': ".format(self.env_name))
        )

    @memoized
    def _get_vault_variables(self):
        # try unencrypted first for tests
        with open(self.vault_file_path, 'r', encoding='utf-8') as f:
            vault_vars = yaml.safe_load(f)
        if isinstance(vault_vars, dict):
            return vault_vars

        while True:
            try:
                vault = Vault(self._get_ansible_vault_password())
                with open(self.vault_file_path, 'r', encoding='utf-8') as vf:
                    return vault.load(vf.read())
            except AnsibleVaultError:
                if os.environ.get('ANSIBLE_VAULT_PASSWORD'):
                    raise
                print('incorrect password')
                self._get_ansible_vault_password.reset_cache(self)

    def _get_secret(self, var_name):
        context = self._get_vault_variables_and_record()
        known_secret_specs_by_name = get_known_secret_specs_by_name()
        if var_name in known_secret_specs_by_name:
            legacy_namespace = known_secret_specs_by_name[var_name].legacy_namespace
            if legacy_namespace in context and var_name in context[legacy_namespace]:
                return context[legacy_namespace][var_name]
        return context[var_name]

    def _set_secret(self, var, value):
        data = self._get_vault_variables() or {}
        data[var] = value
        vault = Vault(self._get_ansible_vault_password())
        with open(self.vault_file_path, 'wb') as vf:
            vault.dump(data, vf)
        self._get_vault_variables.reset_cache(self)

    def _record_vault_loaded_event(self, secrets):
        if (
            self.should_send_vault_loaded_event and
            secrets.get('DATADOG_API_KEY') and
            self.record_to_datadog
        ):
            self.should_send_vault_loaded_event = False
            datadog.initialize(
                api_key=secrets['DATADOG_API_KEY'],
                app_key=secrets['DATADOG_APP_KEY'],
            )
            datadog.api.Event.create(
                title="commcare-cloud vault loaded",
                text=' '.join([shlex_quote(arg) for arg in sys.argv]),
                tags=["environment:{}".format(self.env_name)],
                source_type_name='ansible',
            )

    @contextmanager
    def suppress_datadog_event(self):
        """Prevent "run event" from being sent to datadog

        This is only effective if `self.get_vault_variables()` has not
        yet been called outside of this context manager. If it has been
        called then the event has already been sent and this is a no-op.
        """
        value = self.should_send_vault_loaded_event
        self.should_send_vault_loaded_event = False
        try:
            yield
        finally:
            self.should_send_vault_loaded_event = value
