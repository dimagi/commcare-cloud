#!/usr/bin/env bash
set -e

echo "Check: pip-compile"

pip-compile --output-file=requirements.txt setup.py
git --no-pager diff
git update-index -q --refresh
if ! git diff-index --quiet HEAD --; then
    # Changes
    echo "failure: requirements are inconsistent.  Did you run 'pip-compile --output-file=requirements.txt setup.py'?"
    git checkout requirements.txt  # clean up
    exit 1
fi
# No changes
echo "success: requirements match"
