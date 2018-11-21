#! /bin/bash
set -e

make clean
make

./tests/fail_if_there_is_a_git_diff.sh
