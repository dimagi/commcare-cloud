#! /bin/bash
set -e

for env in $(manage-commcare-cloud get environments)
do
    commcare-cloud ${env} aws-fill-inventory --cached &
done

wait

git diff
git update-index -q --refresh
if git diff-index --quiet HEAD --; then
    # No changes
    exit 0
else
    # Changes
    echo "Hey, did you edit inventory.ini when you should have edited inventory.ini.j2?"
    echo "That's a common cause of this test failure."
    echo "If so, make your change to inventory.ini.j2 and run"
    echo "  cchq <env> aws-fill-inventory --cached"
    echo "to fix this test"
    exit 1
fi
