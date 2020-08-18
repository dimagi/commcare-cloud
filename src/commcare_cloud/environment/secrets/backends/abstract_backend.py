import abc
from contextlib import contextmanager

import six


@six.add_metaclass(abc.ABCMeta)
class AbstractSecretsBackend(object):
    @staticmethod
    def prompt_user_input():
        pass

    @staticmethod
    def get_extra_ansible_args():
        return ()

    @staticmethod
    def get_extra_ansible_env_vars():
        return {}

    @abc.abstractmethod
    def get_generated_variables(self):
        pass

    @abc.abstractmethod
    def get_secret(self, var):
        pass

    @contextmanager
    def suppress_datadog_event(self):
        yield
