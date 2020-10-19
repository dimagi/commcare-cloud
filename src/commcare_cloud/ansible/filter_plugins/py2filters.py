from __future__ import absolute_import, unicode_literals
import six


class FilterModule(object):

    def filters(self):
        return {"replace_if_py2": replace_if_py2}


def replace_if_py2(value, replacement):
    return replacement if six.PY2 else value
