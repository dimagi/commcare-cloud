#! /bin/bash


rm docs/commcare-cloud/commands/index.md
make

git update-index -q --refresh
if git diff-index --quiet HEAD --; then
    # No changes
    exit 0
else
    # Changes
    exit 1
fi
