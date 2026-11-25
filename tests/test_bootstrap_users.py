import os
import pwd
from pathlib import Path
from tempfile import TemporaryDirectory as tempdir
from unittest.mock import patch

import pytest
from unmagic import fixture

from . import ansible

KEY_A = "ssh-ed25519 AAAAa alice@example.com"
KEY_B = "ssh-ed25519 AAAAb bob@example.com"


@fixture
def system():
    """Fake user database; home directories live in a temp dir"""
    with tempdir() as tmp:
        fake = FakeSystem(Path(tmp))
        mod = ansible.import_module("bootstrap_users")
        with (
            patch.object(mod, "get_pwnam", fake.getpwnam),
            patch.object(mod, "get_supplementary_groups", fake.groups_of),
            patch.object(mod.AnsibleModule, "run_command", fake.run_command),
        ):
            yield fake


def bootstrap_users(**args):
    args.setdefault("absent", [])
    args.setdefault("groups", ["dev"])
    return ansible.run("bootstrap_users", args)


def test_create_user():
    fake = system()
    result = bootstrap_users(present={"alice": KEY_A})
    assert result["changed"] is True, result
    assert result["created"] == ["alice"]
    assert result["keys_changed"] == ["alice"]
    assert fake.commands == [
        ["useradd", "--create-home", "--shell", "/bin/bash", "--groups", "dev", "alice"],
    ]
    assert fake.keys("alice") == KEY_A + "\n"
    assert fake.mode("alice", ".ssh") == 0o700
    assert fake.mode("alice", ".ssh/authorized_keys") == 0o600


def test_no_change():
    fake = system()
    fake.add_user("alice", groups=["dev"], keys=KEY_A)
    result = bootstrap_users(present={"alice": KEY_A})
    assert result["changed"] is False, result
    assert fake.commands == []


def test_key_comparison_ignores_blank_lines_and_comments():
    fake = system()
    fake.add_user("alice", groups=["dev"], keys=f"# managed\n\n{KEY_A}\n\n")
    result = bootstrap_users(present={"alice": KEY_A + "\n"})
    assert result["changed"] is False, result


def test_key_order_is_ignored():
    fake = system()
    fake.add_user("ansible", keys=f"{KEY_B}\n{KEY_A}\n")
    result = bootstrap_users(present={"alice": KEY_A, "bob": KEY_B}, shared_user="ansible")
    assert "ansible" not in result["keys_changed"], result


def test_replace_keys():
    fake = system()
    fake.add_user("alice", groups=["dev"], keys=KEY_B)
    result = bootstrap_users(present={"alice": KEY_A})
    assert result["keys_changed"] == ["alice"], result
    assert fake.keys("alice") == KEY_A + "\n"


def test_fix_permissions():
    fake = system()
    fake.add_user("alice", groups=["dev"], keys=KEY_A)
    (fake.home("alice") / ".ssh/authorized_keys").chmod(0o644)
    result = bootstrap_users(present={"alice": KEY_A})
    assert result["keys_changed"] == ["alice"], result
    assert fake.mode("alice", ".ssh/authorized_keys") == 0o600


def test_update_shell_and_groups():
    fake = system()
    fake.add_user("alice", groups=["other"], keys=KEY_A, shell="/bin/sh")
    result = bootstrap_users(present={"alice": KEY_A})
    assert result["updated"] == ["alice"], result
    assert fake.commands == [
        ["usermod", "--shell", "/bin/bash", "--groups", "dev", "alice"],
    ]


def test_shared_user_gets_all_present_keys():
    fake = system()
    fake.add_user("ansible", keys=f"{KEY_A}\nssh-ed25519 AAAAx former@example.com")
    result = bootstrap_users(present={"alice": KEY_A, "bob": KEY_B}, shared_user="ansible")
    assert "ansible" in result["keys_changed"], result
    assert fake.keys("ansible") == f"{KEY_A}\n{KEY_B}\n"


def test_remove_absent_user():
    fake = system()
    fake.add_user("carol")
    result = bootstrap_users(present={}, absent=["carol", "dave"])
    assert result["removed"] == ["carol"], result
    assert fake.commands == [
        ["ps", "-o", "pid=", "-u", "carol"],
        ["userdel", "carol"],
    ]


def test_present_and_absent_conflict():
    system()
    with pytest.raises(ansible.Fail, match="both present and absent"):
        bootstrap_users(present={"alice": KEY_A}, absent=["alice"])


def test_check_mode():
    fake = system()
    fake.add_user("carol")
    result = bootstrap_users(
        present={"alice": KEY_A},
        absent=["carol"],
        shared_user="ansible",
        _ansible_check_mode=True,
    )
    assert result["changed"] is True, result
    assert result["created"] == ["alice"]
    assert result["removed"] == ["carol"]
    assert fake.commands == []
    assert not fake.home("alice").exists()


class FakeSystem:

    def __init__(self, root):
        self.root = root
        self.users = {}
        self.commands = []

    def home(self, name):
        return self.root / name

    def keys(self, name):
        return (self.home(name) / ".ssh/authorized_keys").read_text()

    def mode(self, name, path):
        return (self.home(name) / path).stat().st_mode & 0o7777

    def add_user(self, name, groups=(), keys=None, shell="/bin/bash"):
        self.users[name] = {"shell": shell, "groups": list(groups)}
        home = self.home(name)
        home.mkdir()
        if keys is not None:
            (home / ".ssh").mkdir(mode=0o700)
            path = home / ".ssh/authorized_keys"
            path.write_text(keys)
            path.chmod(0o600)

    def getpwnam(self, name):
        if name not in self.users:
            return None
        uid, gid = os.getuid(), os.getgid()
        shell = self.users[name]["shell"]
        return pwd.struct_passwd(
            (name, "x", uid, gid, "", str(self.home(name)), shell))

    def groups_of(self, name, primary_gid):
        return self.users[name]["groups"]

    def run_command(self, args, check_rc=False, **kw):
        self.commands.append(args)
        cmd, name = args[0], args[-1]
        if cmd == "useradd":
            self.add_user(name, groups=self._opt(args, "--groups"),
                          shell=self._opt(args, "--shell")[0])
        elif cmd == "usermod":
            if "--shell" in args:
                self.users[name]["shell"] = self._opt(args, "--shell")[0]
            if "--groups" in args:
                self.users[name]["groups"] = self._opt(args, "--groups")
        elif cmd == "userdel":
            del self.users[name]
        return 0, "", ""

    @staticmethod
    def _opt(args, flag):
        return args[args.index(flag) + 1].split(",")
