from __future__ import absolute_import, unicode_literals


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
