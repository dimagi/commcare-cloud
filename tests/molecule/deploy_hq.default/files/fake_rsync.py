#!/usr/bin/env python3
#
# Fake rsync for the synchronize module, which runs it on the host itself
# (delegate_to: inventory_hostname) to copy between local dirs:
#
#   rsync <options> --out-format='<<CHANGED>>%i %n%L' <src>/ <dest>/
#
# Copies the contents of <src> into <dest>. With --delete-after, also removes
# what's in <dest> but not in <src>. Prints a <<CHANGED>> line per copied file,
# which synchronize reads to report changed. Remote paths aren't supported.
import filecmp
import os
import shutil
import sys


def main(args):
    options = [a for a in args if a.startswith("-")]
    paths = [a for a in args if not a.startswith("-")]
    if len(paths) != 2 or any(":" in p for p in paths):
        print(f"fake rsync: unsupported args: {args!r}", file=sys.stderr)
        return 2
    src, dest = paths
    if not src.endswith("/"):
        dest = os.path.join(dest, os.path.basename(src))

    os.makedirs(dest, exist_ok=True)
    for root, dirs, files in os.walk(src):
        rel = os.path.relpath(root, src)
        os.makedirs(os.path.join(dest, rel), exist_ok=True)
        for name in files:
            s = os.path.join(root, name)
            d = os.path.join(dest, rel, name)
            if not os.path.exists(d) or not filecmp.cmp(s, d, shallow=False):
                shutil.copy2(s, d)
                print(f"<<CHANGED>>>f+++++++++ {os.path.normpath(os.path.join(rel, name))}")

    if "--delete-after" in options:
        for root, dirs, files in os.walk(dest, topdown=False):
            rel = os.path.relpath(root, dest)
            for name in files + dirs:
                if not os.path.lexists(os.path.join(src, rel, name)):
                    path = os.path.join(root, name)
                    if os.path.isdir(path) and not os.path.islink(path):
                        shutil.rmtree(path)
                    else:
                        os.remove(path)
                    print(f"<<CHANGED>>*deleting {os.path.normpath(os.path.join(rel, name))}")
    return 0


if __name__ == "__main__":
    sys.exit(main(sys.argv[1:]))
