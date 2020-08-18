import getpass
import os
import sys
from contextlib import contextmanager

import datadog.api
import yaml
from ansible.parsing.vault import AnsibleVaultError
from ansible_vault import Vault
from memoized import memoized
from six.moves import shlex_quote

from commcare_cloud.environment.paths import ANSIBLE_DIR
from commcare_cloud.environment.secrets.secrets_schema import get_known_secret_specs


class AnsibleVaultSecretsBackend(object):
    def __init__(self, name, vault_file_path, record_to_datadog=False):
        self.name = name
        self.vault_file_path = vault_file_path
        self.record_to_datadog = record_to_datadog
        self.should_send_vault_loaded_event = True

    @staticmethod
    def get_extra_ansible_args():
        return (
            '--vault-password-file={}/echo_vault_password.sh'.format(ANSIBLE_DIR),
        )

    @staticmethod
    def get_generated_variables():
        secret_specs = get_known_secret_specs()
        secret_specs_by_name = {secret_spec.name: secret_spec for secret_spec in secret_specs}
        generated_variables = {}
        for secret_spec in secret_specs:
            if secret_spec.ansible_var_lowercase:
                ansible_var_name = secret_spec.name.lower()
            else:
                ansible_var_name = secret_spec.name
            expression = secret_spec.get_legacy_reference()
            for var_name in secret_spec.fall_back_to_vars:
                expression += ' | default({})'.format(secret_specs_by_name[var_name].get_legacy_reference())
            if not secret_spec.required:
                if secret_spec.default_overrides_falsy_values:
                    expression += ' | default({}, true)'.format(repr(secret_spec.default).strip('u'))
                else:
                    expression += ' | default({})'.format(repr(secret_spec.default).strip('u'))
            generated_variables[ansible_var_name] = "{{{{ {} }}}}".format(expression)
        return generated_variables

    def get_ansible_vault_password(self):
        """Get ansible vault password

        This method has a side-effect: it records a Datadog event with
        the commcare-cloud command that is currently being run.
        """
        self.get_vault_variables()
        return self._get_ansible_vault_password()

    @memoized
    def get_vault_variables(self):
        """Get ansible vault variables

        This method has a side-effect: it records a Datadog event with
        the commcare-cloud command that is currently being run.
        """
        vault_vars = self._get_vault_variables()
        if "secrets" in vault_vars:
            self.record_vault_loaded_event(vault_vars["secrets"])
        return vault_vars

    @memoized
    def _get_ansible_vault_password(self):
        return (
            os.environ.get('ANSIBLE_VAULT_PASSWORD') or
            getpass.getpass("Vault Password for '{}': ".format(self.name))
        )

    @memoized
    def _get_vault_variables(self):
        # try unencrypted first for tests
        with open(self.vault_file_path, 'r') as f:
            vault_vars = yaml.safe_load(f)
        if isinstance(vault_vars, dict):
            return vault_vars

        while True:
            try:
                vault = Vault(self._get_ansible_vault_password())
                with open(self.vault_file_path, 'r') as vf:
                    return vault.load(vf.read())
            except AnsibleVaultError:
                if os.environ.get('ANSIBLE_VAULT_PASSWORD'):
                    raise
                print('incorrect password')
                self._get_ansible_vault_password.reset_cache(self)

    def get_secret(self, var):
        path = var.split('.')
        context = self.get_vault_variables()
        for node in path:
            context = context[node]
        return context

    def record_vault_loaded_event(self, secrets):
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
                tags=["environment:{}".format(self.name)],
                source_type_name='ansible',
            )

    @contextmanager
    def suppress_vault_loaded_event(self):
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
