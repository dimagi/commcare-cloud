#! /bin/bash
# Verify that python-modernize is a no-op
#
# The python-modernize command below should be updated each time a new
# modernizer fix is applied to the codebase.
#
# undo-modernizations.diff may need to be updated if new lines are added
# that would be, but should not be modernized.

PYVER=$(python --version 2>&1)
[[ $PYVER =~ Python\ 2\. ]] || {
    echo "Skipping modernize test on Python $PYVER"
    exit 0
}

set -e
function do_diff() {
    git --no-pager diff --quiet || echo -e "\nERROR: $1"
    git --no-pager diff --exit-code
}

do_diff "Unexpected diff before modernize"
# use find to exclude python3 scripts
find . -name '*.py' \
    ! -path ./scripts/aws/derive_ses_smtp_password.py \
    ! -path ./scripts/es_snapshot.py \
    ! -path ./src/commcare_cloud/ansible/roles/pg_repack/files/pg_repack.py \
    -exec python-modernize --no-diffs -wnf default --future-unicode {} +
git apply tests/undo-superfluous-modernizations.diff
do_diff "Unexpected diff after modernize"
