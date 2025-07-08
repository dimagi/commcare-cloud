from __future__ import absolute_import, unicode_literals


def _generate_args(*args, **kwargs):
    argv = [str(arg) for arg in args]
    for key, value in kwargs.items():
        if value is False or value is None:
            continue
        elif value is True:
            argv.append('--{}'.format(key))
        elif isinstance(value, (str, int)):
            argv.extend(['--{}'.format(key), str(value)])
        else:
            raise TypeError(
                "Do not know how to interpret {} as a command-line argument: {}"
                .format(type(value), value)
            )
    return argv


def commcare_cloud(*args, show_command=True, **kwargs):
    from .cli_utils import print_command
    from .commcare_cloud import call_commcare_cloud
    argv = _generate_args('commcare-cloud', *args, **kwargs)
    if show_command:
        print_command(argv)
    return call_commcare_cloud(argv)
