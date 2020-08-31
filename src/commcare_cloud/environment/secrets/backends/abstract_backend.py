import abc
from contextlib import contextmanager

import six


@six.add_metaclass(abc.ABCMeta)
class AbstractSecretsBackend(object):

    @classmethod
    @abc.abstractmethod
    def from_environment(cls, environment):
        """Each secrets backend must be able to instantiate itself from an environment object"""

    @abc.abstractproperty
    def name(self):
        """The value to use in meta.yml to reference this secrets backend"""
        pass

    @staticmethod
    def prompt_user_input():
        """
        Gather and save any input required from the user to make this secrets backend work

        If the secret backend requires user input of a password
        calling code can call this function near the top to do that upfront
        rather than letting it be done lazily later.
        """
        pass

    @staticmethod
    def get_extra_ansible_args():
        """
        Return the extra args to pass to ansible to make this secrets backend work
        """
        return ()

    @staticmethod
    def get_extra_ansible_env_vars():
        """
        Return the extra environment variables to pass to ansible to make this secrets backend work
        """
        return {}

    @abc.abstractmethod
    def get_generated_variables(self):
        """
        Return the extra ansible variables to set via `-e @.generated.yml`

        Typically this will be something like

        {"SECRET_KEY": "{{ <ansible expression to fetch SECRET_KEY> }}"}
        """
        pass

    def get_secret(self, var):
        path = var.split('.')
        var_name = path[0]
        sub_path = path[1:]
        value = self._get_secret(var_name)
        for node in sub_path:
            value = value[node]
        return value

    @abc.abstractmethod
    def _get_secret(self, var):
        pass

    @abc.abstractmethod
    def set_secret(self, var, value):
        pass

    @contextmanager
    def suppress_datadog_event(self):
        yield
