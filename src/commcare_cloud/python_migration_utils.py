from __future__ import absolute_import, unicode_literals

from io import open

import six


def open_for_write(path):
    """
    Used for cases where we cannot avoid having a bytes string in PY2 and text string in PY3
    Some examples are:
        - json.dump and json.dumps attempt to write byte strings on PY2, and text strings on PY3
        - same for yaml.dump and yaml.safe_dump
        - passing the file stream into a library that writes byte strings in PY2
    """
    if six.PY2:
        return open(path, "wb")
    return open(path, "w", encoding="utf-8")


def open_for_json_dump(path):
    """
    This ensures compatible file write modes based on Python versions
    Python 2 json.dump and json.dumps create a bytes object
    Python 3 json.dump and json.dumps create a str object
    """
    if six.PY2:
        return open(path, "wb")
    return open(path, "w", encoding="utf-8")


def open_for_yaml_dump(path):
    """
    This ensures compatible file write modes based on Python versions for yaml.dump/safe_dump calls
    """
    if six.PY2:
        return open(path, "wb")
    return open(path, "w", encoding="utf-8")
