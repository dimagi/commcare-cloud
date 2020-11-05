from __future__ import unicode_literals
from io import open


def get_file_contents(path):
    with open(path, encoding='utf-8') as f:
        return f.read()
