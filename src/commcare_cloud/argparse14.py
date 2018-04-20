"""
This file allows us to import argparse 1.4, a future version

not available in the python 2.7's standard library (but is in python3).
This file allows us to use the following relative import statement

  from .argparse14 import ArgumentParser

rather than inlining this manual import magic.
"""
from __future__ import print_function
from __future__ import absolute_import
import pkgutil
from commcare_cloud.environment.paths import get_virtualenv_site_packages_path

site_packages = get_virtualenv_site_packages_path()
argparse = pkgutil.get_importer(site_packages).find_module('argparse').load_module('argparse')

ArgumentParser = argparse.ArgumentParser

__all__ = ['ArgumentParser']
