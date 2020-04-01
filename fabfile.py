from __future__ import absolute_import
from __future__ import print_function
from sys import argv
from time import sleep

print("\nRunning fab directly isn't supported anymore for commcare deploys.\n")

sleep(2)
print("Try running\n")
print(("  commcare-cloud {} deploy".format(argv[1])))
print("\ninstead.")
exit(0)
