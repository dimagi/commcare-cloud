#! /bin/bash
CCHQ_VIRTUALENV=${CCHQ_VIRTUALENV:-cchq}
VENV=~/.virtualenvs/$CCHQ_VIRTUALENV
fail_on_error='false' # if true, prints error message and returns exit code 1

while test $# -gt 0; do
  case "$1" in
    --fail-on-error)
      fail_on_error='true'
      shift
      ;;
    *)
      break
      ;;
  esac
done


# activate virtualenv if it exists, otherwise exit with error
if [ -f "$VENV/bin/activate" ]; then
    VIRTUALENV_NOT_FOUND='false'
    source "$VENV/bin/activate"
elif $fail_on_error; then
    echo "A virtual environment was not found at ${VENV}."
    echo "Try running your cchq command with --control-setup=yes."
    exit 1
else
    VIRTUALENV_NOT_FOUND='true'
fi
