# coding=utf-8
import os
import sys
from clint.textui import puts

from commcare_cloud.colors import color_warning


def patch_environ():
    if 'ANSIBLE_CONFIG' not in os.environ:
        from commcare_cloud.environment.paths import ANSIBLE_DIR
        constants_module = 'ansible.constants'
        if constants_module in sys.modules:
            puts(color_warning(
                "\nSettings in 'ansible.cfg' have not been applied. "
                "'ANSIBLE_CONFIG' environment variable must be set before the '{}' module is imported.\n"
            ).format(constants_module))
        os.environ['ANSIBLE_CONFIG'] = os.path.join(ANSIBLE_DIR, 'ansible.cfg')
