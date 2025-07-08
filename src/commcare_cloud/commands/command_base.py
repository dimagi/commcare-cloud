import abc
import inspect

from clint.textui import puts

from commcare_cloud.colors import color_summary


class CommandBase(metaclass=abc.ABCMeta):
    command = None
    help = None
    aliases = ()
    arguments = ()

    run_setup_on_control_by_default = True

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
        puts(color_summary("[{}] {}".format(self.command, message)))


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
