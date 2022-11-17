#! /bin/bash
CCHQ_VIRTUALENV=${CCHQ_VIRTUALENV:-cchq}
VENV=~/.virtualenvs/$CCHQ_VIRTUALENV
BIONIC_USE_SYSTEM_PYTHON=${BIONIC_USE_SYSTEM_PYTHON:-false}
quiet_mode='false'

while test $# -gt 0; do
  case "$1" in
    -q|--quiet)
      quiet_mode='true'
      shift
      ;;
    *)
      break
      ;;
  esac
done

if [ "$BIONIC_USE_SYSTEM_PYTHON" == "true" ]; then
    echo "The variable BIONIC_USE_SYSTEM_PYTHON is set in your environment."
    echo "This variable should only be used temporarily when it is absolutely necessary to use Python 3.6 on 18.04."
    echo "Please remove this variable from your environment when you are able to use Python 3.10 again."
fi

# if on 18.04 with 3.10 installed, use cchq-3.10 unless $BIONIC_USE_SYSTEM_PYTHON is true
if [ "$BIONIC_USE_SYSTEM_PYTHON" == "false" ] && hash python3.10 2>/dev/null && [ $( source /etc/os-release; echo "$VERSION_ID" ) == "18.04" ]; then
    # only append 3.10 if it is not already in the name
    if [ "$CCHQ_VIRTUALENV" != *"3.10"* ]; then
        CCHQ_VENV_PATH_OLD="$VENV"
        CCHQ_VIRTUALENV=$CCHQ_VIRTUALENV-3.10
    fi
    VENV=~/.virtualenvs/$CCHQ_VIRTUALENV
fi

# activate virtualenv if it exists, otherwise exit with error
if [ -f "$VENV/bin/activate" ]; then
    source "$VENV/bin/activate"
    exit 0
else
    if ! $quiet_mode; then
        echo "A virtual environment was not found at ${VENV}."
        echo "Try running your cchq command with --control-setup=yes."
    fi
    exit 1
fi
