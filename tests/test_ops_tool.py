import doctest

from nose.tools import assert_equal

from commcare_cloud.commands.ansible.ops_tool import chunked, _get_host_key_map


def test_chunked():
    line = 'foo.example.com ssh-rsa AAAABRI= ecdsa-sha2-nistp256 AAAAE2Q='
    hosts, *key_types_keys_list = line.split(' ')
    key_type_key_pairs = chunked(key_types_keys_list, 2)
    assert_equal(list(key_type_key_pairs), [
        ('ssh-rsa', 'AAAABRI='),
        ('ecdsa-sha2-nistp256', 'AAAAE2Q='),
    ])


def test_get_host_key_map():
    known_host_lines = [
        '10.0.0.10 ecdsa-sha2-nistp256 AAAAE2V=',
        '10.0.0.10 ssh-ed25519 AAAATppj',
        '10.0.0.10 ssh-rsa AAAACT5P',
        'foo.example.com ssh-rsa AAAABRI= ecdsa-sha2-nistp256 AAAAE2Q=',
    ]
    keys_by_host = _get_host_key_map(known_host_lines)
    assert_equal(keys_by_host, {
        ('10.0.0.10', 'ecdsa-sha2-nistp256'): 'AAAAE2V=',
        ('10.0.0.10', 'ssh-ed25519'): 'AAAATppj',
        ('10.0.0.10', 'ssh-rsa'): 'AAAACT5P',
        ('foo.example.com', 'ssh-rsa'): 'AAAABRI=',
        ('foo.example.com', 'ecdsa-sha2-nistp256'): 'AAAAE2Q=',
    })


def test_doctests():
    from commcare_cloud.commands.ansible import ops_tool

    results = doctest.testmod(ops_tool)
    assert results.failed == 0
