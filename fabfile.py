from sys import argv
from time import sleep

print("\nRunning fab directly isn't supported anymore for commcare deploys.\n")

sleep(2)
print("Try running\n")
print("  commcare-cloud {} fab deploy".format(argv[1]))
print("\ninstead.")
exit(0)
