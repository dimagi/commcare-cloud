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
    exit 1
fi
