import abc
import six


@six.add_metaclass(abc.ABCMeta)
class CommandBase(object):
    command = None
    help = None
    aliases = ()

    def __init__(self, parser):
        self.parser = parser
        self.make_parser()

    @abc.abstractmethod
    def make_parser(self):
        pass

    @abc.abstractmethod
    def run(self, args, unknown_args):
        pass
