#!/usr/bin/env bash
set -euo pipefail
cd "$(dirname "${BASH_SOURCE[0]}")/../.."

usage() {
  cat <<'EOF'
Usage: run.sh [OPTIONS] [ROLE] [SCENARIO] [ANSIBLE_ARGS]

  run.sh                    Test every scenario for every role
  run.sh <ROLE>             Test every scenario for one role
  run.sh <ROLE> <SCENARIO>  Test one scenario

Options:

  --destroy=never   Leave the container running after the run, e.g. to
                    poke around after a failure.

See also `molecule test --help`. Note: molecule options taking a value
must use --opt=VALUE or -oVALUE syntax.
EOF
}

positional=()
opts=()
args=("$@")
i=0
while [ "$i" -lt "${#args[@]}" ]; do
  arg="${args[$i]}"
  case "$arg" in
    -h|--help)
      usage
      exit 0
      ;;
    -*)
      opts+=("$arg")
      ;;
    *)
      positional+=("$arg")
      ;;
  esac
  i=$((i + 1))
done

role=${positional[0]:-*}
scenario=${positional[1]:-*}
extra=("${positional[@]:2}")

if [[ "$role" == *.* ]]; then
  echo "ROLE must not contain '.'" >&2
  echo "Suggestion: replace '.' with '_': ${role//./_}" >&2
  exit 1
fi

export ANSIBLE_CONFIG=$(pwd)/src/commcare_cloud/ansible/ansible.cfg
export ANSIBLE_ROLES_PATH=$(pwd)/src/commcare_cloud/ansible/roles
export MOLECULE_GLOB="tests/molecule/$role.$scenario/molecule.yml"

molecule test --all ${opts[@]+"${opts[@]}"} ${extra[@]+"${extra[@]}"}
