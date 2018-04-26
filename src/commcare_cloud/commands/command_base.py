import abc
import six


@six.add_metaclass(abc.ABCMeta)
class CommandBase(object):
    command = None
    help = None
    aliases = ()
    arguments = ()

    def __init__(self, parser):
        self.parser = parser

    def make_parser(self):
        for argument in self.arguments:
            argument.add_to_parser(self.parser)

    @abc.abstractmethod
    def run(self, args, unknown_args):
        pass


class Argument(object):
    def __init__(self, *args, **kwargs):
        self._args = args
        self._kwargs = kwargs

    def add_to_parser(self, parser):
        parser.add_argument(*self._args, **self._kwargs)
