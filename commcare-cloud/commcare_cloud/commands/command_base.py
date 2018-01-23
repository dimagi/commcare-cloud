import abc
import six

# this is just to document intent; the subclass will use @classmethod
abstractclassmethod = abc.abstractmethod


@six.add_metaclass(abc.ABCMeta)
class CommandBase(object):
    command = None
    help = None
    aliases = ()

    @abstractclassmethod
    def make_parser(cls, parser):
        pass

    @abstractclassmethod
    def run(cls, args, unknown_args):
        pass
