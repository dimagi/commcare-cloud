# coding=utf-8
from __future__ import print_function
from __future__ import absolute_import

import os
import sys
from clint.textui import puts, colored


def patch_environ():
    if 'ANSIBLE_CONFIG' not in os.environ:
        from commcare_cloud.environment.paths import ANSIBLE_DIR
        constants_module = 'ansible.constants'
        if constants_module in sys.modules:
            puts(colored.red(
                "\nSettings in 'ansible.cfg' have not been applied. "
                "'ANSIBLE_CONFIG' environment variable must be set before the '{}' module is imported.\n"
            ).format(constants_module))
        os.environ['ANSIBLE_CONFIG'] = os.path.join(ANSIBLE_DIR, 'ansible.cfg')
