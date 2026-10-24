"""Tests for the ansible-core 2.11 Python 3.12+ compatibility files

See src/commcare_cloud/ansible/module_utils/README.md
"""
import importlib.util
from pathlib import Path

import ansible as ansible_pkg
import pytest

from . import ansible

MODULE_UTILS = Path(__file__).parent.parent / "src/commcare_cloud/ansible/module_utils"


def _load(name, path):
    spec = importlib.util.spec_from_file_location(name, path)
    module = importlib.util.module_from_spec(spec)
    spec.loader.exec_module(module)
    return module


def test_ansible_core_version():
    # The vendored files are patched copies of ansible-core 2.11.12 files.
    # Delete them (see module_utils/README.md) rather than updating them.
    assert ansible_pkg.__version__ == "2.11.12"


def test_six_meta_importer_supports_find_spec():
    six = _load("vendored_six", MODULE_UTILS / "six/__init__.py")
    assert six.__version__ == "1.17.0"
    assert hasattr(six._SixMetaPathImporter, "find_spec")


def test_https_connection_accepts_client_cert_args():
    urls = _load("vendored_urls", MODULE_UTILS / "urls.py")
    conn = urls.CustomHTTPSConnection("example.com", cert_file=None, key_file=None)
    assert conn.cert_file is None
    assert conn.key_file is None


@pytest.mark.parametrize("value, expected", [
    ("application/json", ("application/json", {})),
    ("text/html; charset=UTF-8", ("text/html", {"charset": "UTF-8"})),
    ('text/plain; Charset="utf-8"; foo=bar', ("text/plain", {"charset": "utf-8", "foo": "bar"})),
    ('multipart/form-data; boundary="a;b"', ("multipart/form-data", {"boundary": "a;b"})),
    ('text/plain; name="a\\"b"', ("text/plain", {"name": 'a"b'})),
    ("Text/HTML", ("Text/HTML", {})),
    ("", ("", {})),
])
def test_uri_parse_content_type(value, expected):
    uri = ansible.import_module("uri")
    assert uri._parse_content_type(value) == expected
