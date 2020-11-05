from __future__ import absolute_import, unicode_literals

from io import open


def get_file_contents(path):
    with open(path, 'r', encoding='utf-8') as f:
        return f.read()
