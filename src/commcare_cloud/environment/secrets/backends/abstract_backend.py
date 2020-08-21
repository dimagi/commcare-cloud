import abc
from contextlib import contextmanager

import six


@six.add_metaclass(abc.ABCMeta)
class AbstractSecretsBackend(object):

    @classmethod
    @abc.abstractmethod
    def from_environment(cls, environment):
        """Each secrets backend must be able to instantiate itself from an environment object"""
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

    @abc.abstractmethod
    def get_secret(self, var):
        pass

    @contextmanager
    def suppress_datadog_event(self):
        yield
