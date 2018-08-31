import abc
import inspect

import six
from clint.textui import puts, colored


@six.add_metaclass(abc.ABCMeta)
class CommandBase(object):
    command = None
    help = None
    aliases = ()
    arguments = ()

    def __init__(self, parser):
        self.parser = parser

    def make_parser(self, for_docs=False):
        for argument in self.arguments:
            if for_docs and not argument.include_in_docs:
                continue
            argument.add_to_parser(self.parser)
        self.modify_parser()

    def modify_parser(self):
        pass

    @abc.abstractmethod
    def run(self, args, unknown_args):
        pass

    def log(self, message):
        puts(colored.magenta("[{}] {}".format(self.command, message)))


class Argument(object):
    def __init__(self, *args, **kwargs):
        self.include_in_docs = kwargs.pop('include_in_docs', True)
        self._args = args
        self._kwargs = kwargs
        if 'help' in self._kwargs:
            self._kwargs['help'] = inspect.cleandoc(self._kwargs['help'])

    def add_to_parser(self, parser):
        parser.add_argument(*self._args, **self._kwargs)


class CommandError(Exception):
    pass
