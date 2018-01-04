#!/bin/bash
#
# Pre-commit hook that verifies if all files containing 'vault' in the name
# are encrypted.
# If not, commit will fail with an error message
#
# File should be .git/hooks/pre-commit and executable
FILES_PATTERN='.*vault.*$'
REQUIRED='ANSIBLE_VAULT'

EXIT_STATUS=0
wipe="\033[1m\033[0m"
yellow='\033[1;33m'
# carriage return hack. Leave it on 2 lines.
cr='
'
for f in $(git diff --cached --name-only | grep -E $FILES_PATTERN)
do
  MATCH=`grep -L $REQUIRED $f | head -n 1`
  if [ -n "${MATCH// }" ] ; then
    UNENCRYPTED_FILES="$f$cr$UNENCRYPTED_FILES"
    EXIT_STATUS=1
  fi
done
if [ $EXIT_STATUS = 0 ] ; then
  exit 0
else
  echo '# COMMIT REJECTED'
  echo '# Looks like unencrypted ansible-vault files are part of the commit:'
  echo '#'
  while read -r line; do
    if [ -n "$line" ]; then
      echo -e "#\t${yellow}unencrypted:   $line${wipe}"
    fi
  done <<< "$UNENCRYPTED_FILES"
  echo '#'
  echo "# Please encrypt them with 'ansible-vault encrypt <file>'"
  echo "#   (or force the commit with '--no-verify')."
  exit $EXIT_STATUS
fi
