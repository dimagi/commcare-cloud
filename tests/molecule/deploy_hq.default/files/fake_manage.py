#!/usr/bin/env python3
# Fake for commcare-hq's manage.py. Appends "manage.py <args>" to the command
# log for verify to check. Creates only what later role tasks need.
import os
import sys

args = sys.argv[1:]
with open("/var/tmp/deploy_hq-commands.log", "a") as log:
    log.write(" ".join(["manage.py", *args]) + "\n")

if args[:1] == ["collectstatic"]:
    os.makedirs("staticfiles", exist_ok=True)
elif args[:1] == ["compress"]:
    os.makedirs("staticfiles/CACHE/js", exist_ok=True)
    with open("staticfiles/CACHE/manifest.json", "w") as f:
        f.write("{}\n")
    with open("staticfiles/CACHE/js/output.js", "w") as f:
        f.write("// compressed\n")
