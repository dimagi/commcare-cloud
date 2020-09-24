
from __future__ import unicode_literals
def get_file_contents(path):
    with open(path, 'r') as f:
        return f.read()
