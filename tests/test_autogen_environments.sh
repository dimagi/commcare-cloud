#! /bin/bash
set -e

for env in $(manage-commcare-cloud get environments)
do
    commcare-cloud ${env} aws-fill-inventory --cached &
done

wait

./tests/fail_if_there_is_a_git_diff.sh \
"Hey, did you edit inventory.ini when you should have edited inventory.ini.j2?
That's a common cause of this test failure.
If so, make your change to inventory.ini.j2 and run
  cchq <env> aws-fill-inventory --cached
to fix this test"
