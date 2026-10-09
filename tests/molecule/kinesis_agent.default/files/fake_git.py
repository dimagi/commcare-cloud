#!/usr/bin/env python3
#
# Fake for ansible.builtin.git checking out a tag. A fresh clone runs:
#
#   git --version
#   git ls-remote <repo> -h refs/heads/<version>
#   git ls-remote <repo> -t refs/tags/<version>
#   git clone --origin origin <repo> <dest>
#   git ls-remote origin -h refs/heads/<version>
#   git checkout --force <version>
#   git rev-parse HEAD
#
# An update of the existing clone (the idempotence run) runs:
#
#   git --version
#   git status --porcelain
#   git rev-parse HEAD
#   git ls-remote --get-url origin
#   git fetch --tags origin
#   git ls-remote origin -h refs/heads/<version>
#   git checkout --force <version>
#   git rev-parse HEAD
#
# clone copies the fixture tree (a fake `setup` script) into <dest>. HEAD is
# always the same sha, so an update never reports changed. Any other command
# fails, so a role change that needs more of git fails loudly.
import os
import shutil
import sys

REPO = "https://github.com/awslabs/amazon-kinesis-agent.git"
FIXTURE = "/var/tmp/fake-kinesis-agent"
SHA = "0123456789abcdef0123456789abcdef01234567"


def main(argv):
    args = argv[1:]

    if args == ["--version"]:
        print("git version 2.34.1")
        return 0

    if len(args) == 4 and args[0] == "ls-remote" and args[2] == "-h":
        return 0  # no branches: the version is a tag

    if len(args) == 4 and args[0] == "ls-remote" and args[2] == "-t":
        print(f"{SHA}\t{args[3]}")
        return 0

    if args[:3] == ["clone", "--origin", "origin"] and len(args) == 5:
        repo, dest = args[3:]
        if repo != REPO:
            return fail("unexpected repo", argv)
        shutil.copytree(FIXTURE, dest, dirs_exist_ok=True)
        os.makedirs(os.path.join(dest, ".git"))
        with open(os.path.join(dest, ".git", "config"), "w") as f:
            f.write(f'[remote "origin"]\n\turl = {repo}\n')
        return 0

    if args == ["status", "--porcelain"]:
        return 0  # no local modifications

    if args == ["ls-remote", "--get-url", "origin"]:
        print(REPO)
        return 0

    if args == ["fetch", "--tags", "origin"]:
        return 0

    if args[:2] == ["checkout", "--force"] and len(args) == 3:
        return 0

    if args == ["rev-parse", "HEAD"]:
        print(SHA)
        return 0

    return fail("unknown command", argv)


def fail(message, argv):
    print(f"fake git: {message}: {argv!r}", file=sys.stderr)
    return 2


if __name__ == "__main__":
    sys.exit(main(sys.argv))
