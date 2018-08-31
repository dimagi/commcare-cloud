import os

from nose_parameterized import parameterized

from commcare_cloud.environment.main import Environment
from commcare_cloud.environment.paths import DefaultPaths

TEST_ENVIRONMENTS_DIR = os.path.join(os.path.dirname(__file__), 'csv_env')
TEST_ENVIRONMENTS = os.listdir(TEST_ENVIRONMENTS_DIR)

EXPECTED_OUTPUT = {
    "hostvars": {
        "192.168.33.26": {
            "datavol_device": "/dev/mapper/consolidated-data",
            "postgresql_replication_slots": [
                "standby",
                "spare"
            ],
            "hostname": "ALIAS_PU00",
            "alt_hostname": "pgucr",
            "hot_standby_server": "192.168.33.27",
            "devices": [
                "/dev/sdb"
            ],
            "partitions": [
                "/dev/sdb1",
                "/dev/sdc"
            ]
        },
        "192.168.33.27": {
            "datavol_device": "/dev/mapper/consolidated-data",
            "hot_standby_master": "192.168.33.26",
            "hostname": "ALIAS_PUS0",
            "alt_hostname": "pgucrstandby0",
            "replication_slot": "standby",
            "devices": [
                "/dev/sda"
            ],
            "partitions": [
                "/dev/sdb1",
                "/dev/sdc1"
            ]
        },
        "192.168.33.21": {
            "hostname": "couch0",
        },
        "192.168.33.22": {
            "hostname": "couch1",
        }
    },
    "test_group1": {
        "children": ["pgucr"],
        "vars": {
            "list_var": [1, 2],
            "float_var": 0.9,
            "integer_var": 3500,
            "integer_var1": 10
        }
    },
    "test_group2": {
        "children": ["pgucrstandby0"],
        "vars": {
            "boolean_var1": True,
            "boolean_var2": False,
            "string_var": "test"
        }
    },
    "couchdb2": {
        "children": ["couch0", "couch1"],
    },
    "lvm": {
        "children": ["couch0", "couch1", "pgucr", "pgucrstandby0"],
    },
    "postgres": {
        "children": ["pgucr"],
        "vars": {
            "var1": "val1"
        }
    },
    "pg_standby": {
        "children": ["pgucrstandby0"],
    },
    "couch0": {
        "hosts": [
            "192.168.33.21"
        ],
    },
    "couch1": {
        "hosts": [
            "192.168.33.22"
        ],
        "children": [],
        "vars": {}
    },
    "pgucr": {
        "hosts": [
            "192.168.33.26"
        ],
    },
    "pgucrstandby0": {
        "hosts": [
            "192.168.33.27"
        ],
    },
    "all": {
        "children": ["ungrouped", "pg_standby", "postgres", "test_group2", "test_group1", "lvm", "couchdb2"],
    },
    "ungrouped": {}
}

HOSTS_BY_GROUP = {
    'all': ['192.168.33.27', '192.168.33.26', '192.168.33.21', '192.168.33.22'],
    'pg_standby': ['192.168.33.27'],
    'postgres': ['192.168.33.26'],
    'couch0': ['192.168.33.21'],
    'couch1': ['192.168.33.22'],
    'pgucr': ['192.168.33.26'],
    'ungrouped': [],
    'test_group2': ['192.168.33.27'],
    'test_group1': ['192.168.33.26'],
    'pgucrstandby0': ['192.168.33.27'],
    'lvm': ['192.168.33.21', '192.168.33.22', '192.168.33.26', '192.168.33.27'],
    'couchdb2': ['192.168.33.21', '192.168.33.22']
}

INTERNAL_HOST_VARS = (
    'inventory_file',
    'inventory_dir',
)

@parameterized(TEST_ENVIRONMENTS)
def test_csv_inventory(env_name):
    env = Environment(DefaultPaths(env_name, environments_dir=TEST_ENVIRONMENTS_DIR))

    for group, hosts in env.sshable_hostnames_by_group.items():
        assert set(hosts) == set(HOSTS_BY_GROUP[group]), "{}: {}".format(group, hosts)

    inventory = env.inventory_manager
    for name, group in inventory.groups.items():
        expected = EXPECTED_OUTPUT[name]
        assert group.vars == expected.get('vars', {}), "{}: {}".format(name, group.vars)
        hosts = {host.name for host in group.hosts}
        assert hosts == set(expected.get('hosts', [])), "{}: {}".format(name, group.hosts)
        children = {child.name for child in group.child_groups}
        assert children == set(expected.get('children', [])), "{}: {}".format(name, group.child_groups)

    for name, host in inventory.hosts.items():
        expected_vars = EXPECTED_OUTPUT["hostvars"][name]
        host_vars = {
            var: val
            for var, val in host.vars.items()
            if var not in INTERNAL_HOST_VARS
        }
        assert host_vars == expected_vars, "{}: {}".format(name, host_vars)
