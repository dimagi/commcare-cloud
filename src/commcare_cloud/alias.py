from __future__ import absolute_import
from __future__ import unicode_literals
import six


def _encode_args(*args, **kwargs):
    argv = []

    def encode_string(value):
        if isinstance(value, six.string_types + six.integer_types):
            return six.text_type(value).encode('utf-8')
        else:
            TypeError("Do not know how to interpret type {} as a command-line argument: {}"
                      .format(type(value), value))
    for arg in args:
        argv.append(six.text_type(arg).encode('utf-8'))
    for key, value in kwargs.items():
        if value is False or value is None:
            continue
        elif value is True:
            argv.append('--{}'.format(key))
        else:
            argv.extend(['--{}'.format(key), encode_string(value)])
    return argv


def _generate_args(*args, **kwargs):
    argv = []

    for arg in args:
        argv.append(arg)
    for key, value in kwargs.items():
        if value is False or value is None:
            continue
        elif value is True:
            argv.append('--{}'.format(key))
        else:
            argv.extend(['--{}'.format(key), value])
    return argv


def commcare_cloud(*args, **kwargs):
    from .cli_utils import print_command
    from .commcare_cloud import call_commcare_cloud
    argv = _generate_args('commcare-cloud', *args, **kwargs)
    print_command(argv)
    return call_commcare_cloud(argv)
