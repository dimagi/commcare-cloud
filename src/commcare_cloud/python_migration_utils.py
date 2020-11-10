from __future__ import absolute_import, unicode_literals

from io import open

import six


def open_for_json_dump(path):
    """
    This ensures compatible file write modes based on Python versions
    Python 2 json.dump and json.dumps create a bytes object
    Python 3 json.dump and json.dumps create a str object
    """
    if six.PY2:
        return open(path, "wb")
    return open(path, "w", encoding="utf-8")
