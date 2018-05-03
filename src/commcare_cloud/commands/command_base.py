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
        self.modify_parser()

    def modify_parser(self):
        pass

    @abc.abstractmethod
    def run(self, args, unknown_args):
        pass


class Argument(object):
    def __init__(self, *args, **kwargs):
        self.include_in_docs = kwargs.pop('include_in_docs', True)
        self._args = args
        self._kwargs = kwargs

    @property
    def name_in_docs(self):
        flag = None
        if not self._args:
            if 'dest' in self._kwargs:
                dest = self._kwargs['dest']
        elif not self._args[0].startswith('-'):
            # positional arg
            if 'dest' in self._kwargs:
                dest = self._kwargs['dest']
            else:
                dest = self._args[0]
        else:
            # non-positional arg
            if self._args[0].startswith('--'):
                # first arg is the long form
                flag = self._args[0]
            elif len(self._args) > 1 and self._args[1].startswith('--'):
                # second arg is the long form
                flag = self._args[1]
            else:
                # use the short form then
                flag = self._args[0]
            if 'dest' in self._kwargs:
                dest = self._kwargs['dest']
            else:
                dest = flag.lstrip('-')

        if flag and self._kwargs.get('action') in ('store_true', 'store_false'):
            return flag
        if flag:
            return '{} <{}>'.format(flag, dest.replace('-', '_'))
        else:
            return '<{}>'.format(dest.replace('-', '_'))

    def add_to_parser(self, parser):
        parser.add_argument(*self._args, **self._kwargs)
