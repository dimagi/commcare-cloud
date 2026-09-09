#!/usr/bin/env bash
set -euo pipefail
cd "$(dirname "${BASH_SOURCE[0]}")/../.."

usage() {
  cat <<'EOF'
Usage: run.sh [OPTIONS] [ROLE] [SCENARIO] [ANSIBLE_ARGS]

  run.sh                    Test every scenario for every role
  run.sh <ROLE>             Test every scenario for one role
  run.sh <ROLE> <SCENARIO>  Test one scenario

Useful options (see `molecule test --help` for all):

  --destroy never   Leave the container running after the run, e.g. to
                    poke around after a failure.
  --parallel        Run scenarios in parallel.
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
    # These take a separate value argument (not just --opt=value); pull
    # both tokens so the value isn't mistaken for ROLE/SCENARIO.
    -s|--scenario-name|-p|--platform-name|-d|--driver-name|--destroy)
      opts+=("$arg" "${args[$((i + 1))]}")
      i=$((i + 1))
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

export ANSIBLE_CONFIG=$(pwd)/src/commcare_cloud/ansible/ansible.cfg
export ANSIBLE_ROLES_PATH=$(pwd)/src/commcare_cloud/ansible/roles
export MOLECULE_GLOB="tests/molecule/$role-$scenario/molecule.yml"

molecule test --all ${opts[@]+"${opts[@]}"} ${extra[@]+"${extra[@]}"}
