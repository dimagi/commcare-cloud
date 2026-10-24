# Python 3.12+ compatibility for ansible-core 2.11

`compat(ansible-core-2.11)`: find everything to remove with `git grep 'compat(ansible-core-2.11)'`.

commcare-cloud pins `ansible~=4.3` (ansible-core 2.11), which predates
Python 3.12. Ansible runs modules with the target's `/usr/bin/python3`,
which is Python 3.14 on Ubuntu 26.04, so some of the code ansible-core
ships to targets no longer imports there.

Ansible checks this directory (`module_utils` in `ansible.cfg`) before its
own `ansible.module_utils` package, and `../library` before its builtin
modules, so these files replace the ansible-core versions on every target.
They also work with Python 3.10 (Ubuntu 22.04).

| File | Upstream | Change |
|---|---|---|
| `six/__init__.py` | six 1.17.0, unmodified | ansible-core 2.11 bundles six 1.13, whose meta path importer only implements `find_module()`/`load_module()`, removed in Python 3.12. Every module fails with `No module named 'ansible.module_utils.six.moves'`. |
| `urls.py` | ansible-core 2.11.12 `lib/ansible/module_utils/urls.py` | Python 3.12 removed the `cert_file`/`key_file` arguments and attributes of `http.client.HTTPSConnection`, breaking `get_url`, `apt_key url=` and other HTTPS fetches. |
| `../library/uri.py` | ansible-core 2.11.12 `lib/ansible/modules/uri.py` | Python 3.13 removed `cgi`; `cgi.parse_header()` is inlined. |

Delete this directory, `../library/uri.py` and the `module_utils` line in
`ansible.cfg` when ansible-core is upgraded to 2.15 or later, which fixes all
of the above upstream. `tests/test_ansible_py312_compat.py` fails when the
installed ansible-core version changes as a reminder.
