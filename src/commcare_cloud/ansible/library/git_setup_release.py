#! /usr/bin/env python3
import os
import signal
from configparser import ConfigParser
from os.path import basename
from pathlib import Path

from ansible.module_utils.basic import AnsibleModule

__metaclass__ = type


DOCUMENTATION = """
---
module: git_setup_release

short_description: Efficiently clone a git repository with submodules.

version_added: "1.0.0"

description: Use shared reference "mirror" repositories to efficiently clone
and checkout releases with git.

options:
    repo:
        description: Repository URL.
        required: true
        type: str
    version:
        description: Release version (a git rev).
        required: true
        type: str
    dest:
        description: Release directory path.
        required: true
        type: str
    reference:
        description: Path to directory containing mirror repositories.
            New repositories will be created here if they do not exist.
        required: true
        type: str
    key_file:
        description: Optional key file to use for remote git operations.
        required: false
        type: str
    previous_release:
        description: Previous release path.
        required: false
        type: str

extends_documentation_fragment:
    - commcare_cloud.ansible

author:
    - Daniel Miller (@millerdev)
"""

EXAMPLES = """
- name: Setup release
  git_setup_release:
    repo: https://github.com/example/project
    version: main
    dest: /opt/releases/two
    reference: /opt/releases/src
    previous_release: /opt/releases/one
"""

RETURN = """
changed:
    description: Changed flag.
    type: bool
diff:
    description: Dict of before and after states of repositories
                 (main + submodules) and their versions.
    type: dict
    sample: {'before': {'path': ...}, 'after': {'path': ...}}
dest:
    description: Destination path, equal to the value passed to I(dest).
    type: str
    sample: /path/to/release/
"""


def main():
    module_args = {
        'repo': {'type': 'str', 'required': True},
        'version': {'type': 'str', 'required': True},
        'dest': {'type': 'str', 'required': True},
        'reference': {'type': 'str', 'required': True},
        'key_file': {'type': 'str', 'required': False, 'default': None},
        'previous_release': {'type': 'str', 'required': False, 'default': None},
    }
    module = AnsibleModule(
        argument_spec=module_args,
        supports_check_mode=True
    )
    params = module.params
    dest = Path(params["dest"])
    prev_ = params.get("previous_release")
    prev = dest if prev_ is None else Path(prev_).resolve()
    diff = {'before': {'path': str(prev)}, 'after': {'path': str(dest)}}
    result = {'changed': False, 'dest': str(dest), 'diff': diff}

    if not dest.exists():
        if not params["version"]:
            msg = "Cannot setup release without code version."
            return module.fail_json(msg=msg, **result)

        # temporary name facilitates idempotent release setup
        dest_tmp = dest.with_name(dest.name + ".tmp")
        result["changed"] = True
        if module.check_mode:
            if dest_tmp.exists():
                return incomplete_release(dest_tmp, module, result)
        else:
            prev_dir = os.getcwd()
            try:
                dest_tmp.mkdir()
            except OSError:
                if not dest.parent.exists():
                    return module.fail_json(msg=f"missing: {dest.parent}", **result)
                return incomplete_release(dest_tmp, module, result)
            # Race condition warning: a SIGHUP signal caused by events
            # such as SSH disconnect, which can happen if the Ansible
            # operator issues a keyboard interrupt precisely between
            # when ``dest_tmp`` is created and the next ``try`` block is
            # entered, will result in a permanent "incomplete release"
            # failure if a subsequent ``git_setup_release`` attempts to
            # reuse the same release directory (``dest``). This could
            # happen when resuming an interrupted deploy, for example.
            #
            # https://docs.python.org/3/library/signal.html#note-on-signal-handlers-and-exceptions
            try:
                signal.signal(signal.SIGHUP, handle_ssh_disconnect)
                mirrors_path = Path(params["reference"])
                key_file = params["key_file"]
                release = Release(mirrors_path, module.run_command, diff, key_file)
                release.setup(dest_tmp, params["repo"], params["version"], prev)
            except BaseException:
                os.chdir(prev_dir)  # module.run_command does not reset cwd on error
                dest_tmp.rename(get_fail_path(dest))
                raise
            dest_tmp.rename(dest)

    module.exit_json(**result)


class Release:

    def __init__(self, mirrors_path, run_command, diff, key_file=None):
        self.mirrors_path = mirrors_path
        self.run_command = run_command
        self.diff = diff
        self.key_file = key_file
        self.seen = {}

    def setup(self, release_path, repo_url, version, prev):
        name = basename(repo_url.rstrip("/"))
        if not name:
            raise ValueError(f"invalid repository URL: {repo_url}")
        if not name.endswith(".git"):
            name += ".git"
        seen = self.seen
        if name in seen and seen[name] != repo_url:
            raise ValueError(f"URL conflict for {name}: {seen[name]} != {repo_url}")
        seen[name] = repo_url
        repo_mirror = self.mirrors_path / name

        if (prev / ".git").exists():
            self.diff['before'][repo_url] = self.get_version(prev)
        if not repo_mirror.exists():
            self.run(["git", "clone", "--mirror", repo_url, repo_mirror])
        else:
            self.run(["git", "remote", "update", "--prune"], cwd=repo_mirror)

        self.run(["git", "clone", "--no-checkout", "--reference", repo_mirror, repo_url, release_path])
        self.run(["git", "checkout", version], cwd=release_path)
        self.diff['after'][repo_url] = self.get_version(release_path)

        # could save time by doing these in parallel
        for path, url, subversion in self.iter_submodules(release_path):
            sub_path = release_path / path
            prev_path = prev / path
            self.setup(sub_path, url, subversion, prev_path)

    def iter_submodules(self, repo_path):
        gitmodules = repo_path / ".gitmodules"
        if not gitmodules.exists():
            return
        modules = ConfigParser()
        with open(gitmodules) as fh:
            modules.read_file(fh)
        for section in modules.sections():
            mod = modules[section]
            cmd = ["git", "ls-tree", "-z", "-d", "HEAD", "--", mod["path"]]
            version = self.run(cmd, cwd=repo_path).split()[2]
            yield mod["path"], mod["url"], version

    def get_version(self, git_repo):
        return self.run(["git", "rev-parse", "HEAD"], cwd=git_repo).strip()

    def run(self, args, **kw):
        kw.setdefault("check_rc", True)
        if self.key_file:
            ssh = f"ssh -i {self.key_file}"
            kw.setdefault("environ_update", {})["GIT_SSH_COMMAND"] = ssh
        rc, stdout, stderr = self.run_command(args, **kw)
        return stdout


def incomplete_release(dest_tmp, module, result):
    msg = (
        f"Found incomplete release: {dest_tmp}\nIs there another "
        "release in progress? If not, the best course of action is "
        "to abandon this one and try again with a new release name."
    )
    return module.fail_json(msg=msg, **result)


def get_fail_path(path):
    i = 1
    while True:
        failed = path.with_name(path.name + f".fail-{i}")
        if not failed.exists():
            return failed
        i += 1


def handle_ssh_disconnect(signum, frame):
    # convert signal to exception to allow cleanup
    raise KeyboardInterrupt


if __name__ == '__main__':
    main()
