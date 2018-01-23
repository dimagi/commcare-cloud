from __future__ import print_function
from __future__ import absolute_import
import pkgutil
import sys
import os

for filepath in sys.path:
    if os.path.isdir(filepath) and 'argparse.py' in os.listdir(filepath):
        argparse = pkgutil.get_importer(filepath).find_module('argparse').load_module('argparse')
else:
    import argparse

ArgumentParser = argparse.ArgumentParser

__all__ = ['ArgumentParser']
