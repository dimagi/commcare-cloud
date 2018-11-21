from __future__ import (absolute_import, division, print_function)

import csv
import json
import os

__metaclass__ = type

DOCUMENTATION = '''
    inventory: csv
    short_description: Uses CSV files and inventory source.
    description: |
        - CSV file based inventory, lines are split into groups by a blank line.
        - Each group of lines can either be a list of hosts or a list of group var definitions.
        - Hosts are listed with the following required fields (C(hostname), C(host_address))
        - Host groups are specified in group columns e.g. C(group 1), C(group 2) etc.
        - Host vars are listed in individual colums with headers formatted as follows - C({type}.var: {name}).
        - The 'type' field must be one of the following (or blank for the default)
            - S: string (default if no type specified)
            - B: boolean ('true' or 't' (case insensitive), anything else is false)
            - I: integer
            - F: float
            - L: list (formatted as JSON)
            - H: host (resolve to an ansible host. Only supported in host lists within the same block)
        - Group vars can be defined in two formats. The first is similar to hosts where each row is a group
        and columns are variables. The second format has 4 columns, C(group), C(var), C(val), C(type) and
        each row represents a single variable value for a single group.
        - In both formats the first column header must be C(group).
    notes:
       - "The hostname of a host defaults to the value in the 'hostname' column but it can be overridden by
         adding a C(var: hostname) var column."
       - If this is done then the value in the C(hostname) column will be set as the value of the C(alt_hostname) var.
'''

EXAMPLES = '''
  example1: |
      # host list with groups and host vars
      hostname,  host_address,   group 1,   group 2,  var: v1,  I.var: v2, L.var: v3
      host1,     192.168.33.21,  web,       ,         val1,     23,
      host2,     192.168.33.22,  proxy,     nginx,    val2,     23,
      host3,     192.168.33.23,  db,        lvm,      val3,     ,          ["v1", "v2"]

      # group vars definition table (row format)
      group,   var,         val,             type
      web,     gvar1,       1,               I
      web,     gvar2,       foo,             S
      nginx,   nginx_port,  80,              I
      all,     whitelist,   ["a", "b"],      L

  example2: |
      # separate groups of hosts can have their own headers
      hostname,  host_address,   group 1,   group 2,  var: v1
      host1,     192.168.33.21,  web,       ,         val1
      host2,     192.168.33.22,  proxy,     nginx,    val2

      # comments are ignored
      # groups are separated by a blank line (or a line where the first cell is cells)
      hostname,  host_address,   group 1,   I.var: db_port,  var: root_path
      host3,     192.168.33.23,  db,        1234,            /opt/data/db
      
      # group table (column format)
      group,  var: port,  var: relay
      g1,     9010,       True
      g2,     8000,       False
'''


from ansible.errors import AnsibleParserError
from ansible.module_utils._text import to_text, to_bytes
from ansible.plugins.inventory import BaseInventoryPlugin


TYPE_STRING = 'S'
TYPE_INTEGER = 'I'
TYPE_BOOLEAN = 'B'
TYPE_FLOAT = 'F'
TYPE_LIST = 'L'
TYPE_HOST = 'H'


class InventoryModule(BaseInventoryPlugin):
    """Host inventory parser for ansible using csv files."""

    NAME = 'csv'

    def __init__(self):
        super(InventoryModule, self).__init__()

        self._hosts = set()

    def verify_file(self, path):
        """Verify if file is usable by this plugin, base does minimal accesability check"""
        valid = False
        if super(InventoryModule, self).verify_file(path):
            file_name, ext = os.path.splitext(path)
            if not ext or ext in ('.csv', '.CSV'):
                valid = True
        return valid

    def parse(self, inventory, loader, path, cache=False):
        super(InventoryModule, self).parse(inventory, loader, path)

        try:
            if self.loader:
                (b_data, private) = self.loader._get_file_contents(path)
            else:
                b_path = to_bytes(path, errors='surrogate_or_strict')
                with open(b_path, 'rb') as fh:
                    b_data = fh.read()

            # Faster to do to_text once on a long string than many
            # times on smaller strings
            data = to_text(b_data, errors='surrogate_or_strict').splitlines()

            self._parse(data)
        except Exception as e:
            raise AnsibleParserError(e)

    def _parse(self, lines):
        row_groups = self._parse_row_groups(lines)
        for row_group in row_groups:
            rows = list(csv.DictReader(row_group))
            if 'hostname' in rows[0]:
                self._parse_hosts(rows)
            elif 'group' in rows[0]:
                self._parse_groups(rows)

    def _parse_hosts(self, rows):
        hosts_aliases = {
            row['hostname']: row['host_address']
            for row in rows
        }

        for row in rows:
            groups = self._get_host_groups(row)
            host_vars = self._get_host_vars(row, hosts_aliases)
            host = row['host_address']
            host_group = row['hostname']
            self.inventory.add_group(host_group)
            self.inventory.add_host(host, host_group)
            for group in groups:
                self.inventory.add_group(group)
                self.inventory.add_child(group, host_group)

            self._populate_host_vars([host], host_vars)

    def _get_host_groups(self, row):
        return [
            val.strip() for key, val in row.items()
            if key.startswith('group') and val.strip()
        ]

    def _get_host_vars(self, row, hosts_aliases):
        vars = {}
        for key, raw_val in row.items():
            raw_val = raw_val.strip()
            if 'var' in key and raw_val:
                item_type, name = key.split('.') if '.' in key else ('S', key)
                name = name.split(' ')[1]
                vars[name] = conv_str2value(item_type, raw_val, hosts_aliases)
        if 'hostname' not in vars:
            vars['hostname'] = row['hostname']
        else:
            vars['alt_hostname'] = row['hostname']
        return vars

    def _parse_groups(self, rows):
        if 'var' in rows[0] and 'val' in rows[0]:
            # row format
            for row in rows:
                group = row['group']
                self.inventory.add_group(group)
                var_name, item_type, raw_val = row['var'], row['type'], row['val'].strip()
                self.inventory.set_variable(group, var_name, conv_str2value(item_type, raw_val))
        else:
            # column format
            for row in rows:
                group = row['group']
                del row['group']
                self.inventory.add_group(group)
                for key, raw_val in row.items():
                    raw_val = raw_val.strip()
                    if 'var' in key and raw_val:
                        item_type, name = key.split('.') if '.' in key else ('S', key)
                        name = name.split(' ')[1]
                        self.inventory.set_variable(group, name, conv_str2value(item_type, raw_val))

    def _parse_row_groups(self, csv_lines):
        """Parse CSV lines into groups each with their own header column"""
        row_groups = []
        current_group = []
        for line in csv_lines:
            if line.startswith('#'):
                continue
            if not line.strip() or line.startswith(','):
                if current_group:
                    row_groups.append(current_group)
                    current_group = []
            else:
                current_group.append(line)
        if current_group:
            row_groups.append(current_group)
        return row_groups


def conv_str2value(item_type, item, hosts_aliases=None):
    """
    Convert a character string to a specified data type.

    :param string item_type: A character string representing the type of item data.
    :param string item: Value of item data.
    :return: The converted value.
    """

    if len(item) <= 0:
        return None

    if TYPE_STRING == item_type:
        return item
    elif TYPE_INTEGER == item_type:
        return int(item)
    elif TYPE_BOOLEAN == item_type:
        item = item.lower()
        return item in ('true', 't')
    elif TYPE_FLOAT == item_type:
        return float(item)
    elif TYPE_LIST == item_type:
        return json.loads(item)
    elif TYPE_HOST == item_type:
        if hosts_aliases is None:
            raise AnsibleParserError("Var of type host not supported: {}".format(item))
        return hosts_aliases.get(item, item)

    return item
