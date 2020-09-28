"""
This file allows us to import argparse 1.4, a future version

not available in the python 2.7's standard library (but is in python3).
This file allows us to use the following relative import statement

  from .argparse14 import ArgumentParser

rather than inlining this manual import magic.
"""
from __future__ import print_function
from __future__ import absolute_import
from __future__ import unicode_literals
import pkgutil
from distutils.sysconfig import get_python_lib

import six


site_packages = get_python_lib()
argparse = pkgutil.get_importer(site_packages).find_module('argparse').load_module('argparse')

ArgumentParser = argparse.ArgumentParser
RawTextHelpFormatter = argparse.RawTextHelpFormatter
SubParsersAction = argparse._SubParsersAction

if six.PY2:
    from collections import OrderedDict

    class SubParsersAction(argparse._SubParsersAction):
        """Sorted choices subparser action

        Not necessary in Python 3.6+ because dicts are ordered there.
        """
        def __init__(self, *args, **kw):
            super(SubParsersAction, self).__init__(*args, **kw)
            assert not self.choices, self.choices
            assert self.choices is self._name_parser_map
            self.choices = self._name_parser_map = OrderedDict()

    class ArgumentParser(argparse.ArgumentParser):
        def add_subparsers(self, **kwargs):
            kwargs.setdefault("action", SubParsersAction)
            return super(ArgumentParser, self).add_subparsers(**kwargs)

__all__ = ['ArgumentParser', 'RawTextHelpFormatter', 'SubParsersAction']
