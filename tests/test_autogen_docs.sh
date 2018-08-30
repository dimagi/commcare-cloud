#! /bin/bash
set -e

make clean
make

git diff
git update-index -q --refresh
if git diff-index --quiet HEAD --; then
    # No changes
    exit 0
else
    # Changes
    exit 1
fi
