import six


def _encode_args(*args, **kwargs):
    argv = []

    def encode_string(value):
        if isinstance(value, six.string_types + six.integer_types):
            return unicode(value).encode('utf-8')
        else:
            TypeError("Do not know how to interpret type {} as a command-line argument: {}"
                      .format(type(value), value))
    for arg in args:
        argv.append(unicode(arg).encode('utf-8'))
    for key, value in kwargs.items():
        if value is False or value is None:
            continue
        elif value is True:
            argv.append('--{}'.format(key))
        else:
            argv.extend(['--{}'.format(key), encode_string(value)])
    return argv


def commcare_cloud(*args, **kwargs):
    from .cli_utils import print_command
    from .commcare_cloud import call_commcare_cloud
    argv = _encode_args('commcare-cloud', *args, **kwargs)
    print_command(argv)
    return call_commcare_cloud(argv)
