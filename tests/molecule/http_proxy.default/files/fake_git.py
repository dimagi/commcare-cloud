#!/usr/bin/env python3
#
# Fake for community.general.git_config, which shells out to
# `git config --includes --global [--get-all] <key>` to read, then
# `git config --includes --global [--replace-all] <key> <value>` to
# conditionally write.
import os
import sys

STATE = os.path.expanduser("~/.gitconfig-fake")
ERRORS = os.path.expanduser("~/.gitconfig-errors")
FLAGS = {"--global", "--get-all", "--replace-all"}


def main(argv):
    if argv[1:3] != ["config", "--includes"]:
        log_error("unknown command", argv)
        return 2

    args = [a for a in argv[3:] if a not in FLAGS]
    entries = read_state()

    if len(args) == 1:  # get
        key = args[0]
        if key in entries:
            print(entries[key])
            return 0
        return 1

    if len(args) == 2:  # replace
        key, value = args
        entries[key] = value
        write_state(entries)
        return 0

    log_error("unknown args", argv)
    return 2


def log_error(message, argv):
    with open(ERRORS, "a") as f:
        f.write(f"{message}: {argv!r}\n")


def read_state():
    entries = {}
    if os.path.exists(STATE):
        with open(STATE) as f:
            for line in f:
                if " " in line:
                    key, _, value = line.rstrip("\n").partition(" ")
                    entries[key] = value
    return entries


def write_state(entries):
    with open(STATE, "w") as f:
        for key, value in entries.items():
            f.write(f"{key} {value}\n")


if __name__ == "__main__":
    sys.exit(main(sys.argv))
