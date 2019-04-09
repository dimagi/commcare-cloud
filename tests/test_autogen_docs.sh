#! /bin/bash
set -e

make clean
make

./tests/fail_if_there_is_a_git_diff.sh || echo "
If you're getting a failure here with a change to the changelog docs
make sure you're following the directions in
https://github.com/dimagi/commcare-cloud/blob/master/changelog/README.md
and not editing changelog markdown files directly.
"
