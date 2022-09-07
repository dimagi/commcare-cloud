#! /bin/bash

set -e

PYVER=$(python --version 2>&1)
if [[ $PYVER =~ Python\ 3\.10 ]]; then
    echo "Skipping requirements test on $PYVER"
    exit 0
fi

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
