from __future__ import absolute_import
from __future__ import unicode_literals

from ansible.parsing.yaml.dumper import AnsibleDumper
from ansible.utils.unsafe_proxy import AnsibleUnsafeText


def represent_unsafe_unicode(dumper, data):
    return dumper.represent_scalar('!unsafe', data)


class PreserveUnsafeDumper(AnsibleDumper):
    """YAML Dumper that preserves the '!unsafe' tag for unsafe values.

    See https://docs.ansible.com/ansible/latest/user_guide/playbooks_advanced_syntax.html#unsafe-or-raw-strings
    """
    pass


PreserveUnsafeDumper.add_representer(
    AnsibleUnsafeText,
    represent_unsafe_unicode,
)
