import os

import pytest
import yaml

from commcare_cloud.manage_commcare_cloud.install import (
    parse_collections,
    parse_roles,
    required_collections,
    required_roles,
)
from commcare_cloud.environment.paths import ANSIBLE_DIR


def test_parse_roles():
    assert parse_roles(ROLE_LIST_OUTPUT) == {
        ('tmpreaper', '46f8e0b8b8f5732eecc68b08b5e0c392c418e3f3'),
        ('ansible-logrotate', 'v0.0.5'),
        ('DavidWittman.redis', '1.2.12'),
        ('andrewrothstein.couchdb', 'fcb957ed038ab1c4fddcfef6b9c7617dcdeec9b7'),
    }


ROLE_LIST_OUTPUT = """
# /home/vagrant/commcare-cloud/.venv/lib/python3.10/site-packages/.ansible/roles
- tmpreaper, 46f8e0b8b8f5732eecc68b08b5e0c392c418e3f3
- ansible-logrotate, v0.0.5
- DavidWittman.redis, 1.2.12
- andrewrothstein.couchdb, fcb957ed038ab1c4fddcfef6b9c7617dcdeec9b7
"""


def test_parse_collections_keeps_same_name_at_different_versions():
    # community.general is present in two paths at different versions; both kept.
    assert parse_collections(COLLECTION_LIST_OUTPUT) == {
        ('amazon.aws', '1.5.1'),
        ('community.general', '3.8.3'),
        ('community.general', '7.4.0'),
        ('dimagi.commcare_logstash', '0.9.5'),
        ('dimagi.commcare_prometheus', '0.1.10'),
    }


COLLECTION_LIST_OUTPUT = """
# /home/vagrant/commcare-cloud/.venv/lib/python3.10/site-packages/ansible_collections
Collection                    Version
----------------------------- -------
amazon.aws                    1.5.1
community.general             3.8.3

# /home/vagrant/commcare-cloud/.venv/lib/python3.10/site-packages/.ansible/ansible_collections
Collection                 Version
-------------------------- -------
community.general          7.4.0
dimagi.commcare_logstash   0.9.5
dimagi.commcare_prometheus 0.1.10
"""


def test_required_roles_and_required_collections_on_requirements_yml():
    with open(os.path.join(ANSIBLE_DIR, "requirements.yml")) as f:
        yml = yaml.safe_load(f)
    assert required_roles(yml), "expected required roles"
    assert required_collections(yml), "expected required collections"


def test_required_roles_uses_name_or_src():
    requirements = {'roles': [
        {'src': 'git+https://github.com/ANXS/tmpreaper.git',
         'version': '46f8e0b8', 'name': 'tmpreaper'},
        {'src': 'sansible.logstash', 'version': 'v2.4.4'},
    ]}
    assert required_roles(requirements) == {
        ('tmpreaper', '46f8e0b8'),
        ('sansible.logstash', 'v2.4.4'),
    }


def test_required_collections():
    requirements = {'collections': [
        {'name': 'community.general', 'version': '7.4.0'},
        {'name': 'dimagi.commcare_logstash', 'version': '0.9.5',
         'source': 'https://example.com/x.tar.gz', 'type': 'url'},
    ]}
    assert required_collections(requirements) == {
        ('community.general', '7.4.0'),
        ('dimagi.commcare_logstash', '0.9.5'),
    }


def test_required_collections_without_version_raises():
    requirements = {'collections': [{'name': 'community.general'}]}
    with pytest.raises(ValueError):
        required_collections(requirements)
