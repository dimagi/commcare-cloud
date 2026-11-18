import os
import tempfile

import pytest
import yaml
from unmagic import fixture

from commcare_cloud.manage_commcare_cloud.install import (
    parse_collections,
    parse_roles,
    remove_unrequired_collections,
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
"""


def test_required_roles_on_requirements_yml():
    with open(os.path.join(ANSIBLE_DIR, "requirements.yml")) as f:
        yml = yaml.safe_load(f)
    assert required_roles(yml), "expected required roles"


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


@fixture
def collections_dir():
    with tempfile.TemporaryDirectory() as path:
        yield path


def make_collection(collections_path, name, version=None):
    namespace, collection = name.split('.')
    root = os.path.join(collections_path, 'ansible_collections')
    os.makedirs(os.path.join(root, namespace, collection))
    if version:
        os.makedirs(os.path.join(root, f"{name}-{version}.info"))


def list_tree(collections_path):
    root = os.path.join(collections_path, 'ansible_collections')
    return sorted(
        os.path.relpath(os.path.join(dirpath, d), root)
        for dirpath, dirnames, _ in os.walk(root)
        for d in dirnames
    )


@collections_dir
def test_remove_unrequired_collections_removes_stale_collection_and_info():
    path = collections_dir()
    make_collection(path, 'community.general', '7.4.0')
    make_collection(path, 'dimagi.commcare_logstash')

    removed = remove_unrequired_collections(path, {'dimagi.commcare_logstash'})

    assert removed == ['community.general']
    assert list_tree(path) == ['dimagi', 'dimagi/commcare_logstash']


@collections_dir
def test_remove_unrequired_collections_keeps_namespace_with_required_collection():
    path = collections_dir()
    make_collection(path, 'community.general', '7.4.0')
    make_collection(path, 'community.postgresql', '3.0.0')

    removed = remove_unrequired_collections(path, {'community.postgresql'})

    assert removed == ['community.general']
    assert list_tree(path) == [
        'community',
        'community.postgresql-3.0.0.info',
        'community/postgresql',
    ]


@collections_dir
def test_remove_unrequired_collections_without_collections_dir():
    assert remove_unrequired_collections(collections_dir(), set()) == []
