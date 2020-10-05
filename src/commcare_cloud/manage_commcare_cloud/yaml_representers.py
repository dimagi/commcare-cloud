from __future__ import absolute_import
from __future__ import unicode_literals

import yaml
from yaml.representer import SafeRepresenter
import six


class LiteralUnicode(six.text_type):
    pass


def change_style(style, representer):
    def new_representer(dumper, data):
        scalar = representer(dumper, data)
        scalar.style = style
        return scalar
    return new_representer


if six.PY3:
    safe_represent = SafeRepresenter.represent_str
else:
    safe_represent = SafeRepresenter.represent_unicode
represent_literal_unicode = change_style('|', safe_represent)
yaml.add_representer(LiteralUnicode, represent_literal_unicode, Dumper=yaml.SafeDumper)
