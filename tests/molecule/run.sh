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

  -c, --command COMMAND
                    Run `molecule COMMAND` instead of `molecule test`,
                    e.g. converge, idempotence, verify, destroy. For
                    fast idempotence iteration: `molecule converge`
                    once, then `molecule idempotence` repeatedly,
                    against the same still-running instance.
                    Requires ROLE and SCENARIO.
  --destroy=never   Leave the container running after the run, e.g. to
                    poke around after a failure.

See also `molecule test --help`. Note: molecule options taking a value
must use --opt=VALUE or -oVALUE syntax.
EOF
}

positional=()
opts=()
command=test
args=("$@")
i=0
while [ "$i" -lt "${#args[@]}" ]; do
  arg="${args[$i]}"
  case "$arg" in
    -h|--help)
      usage
      exit 0
      ;;
    -c|--command)
      command="${args[$((i + 1))]}"
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

if [[ "$role" == *.* ]]; then
  echo "ROLE must not contain '.'" >&2
  echo "Suggestion: replace '.' with '_': ${role//./_}" >&2
  exit 1
fi

if [[ "$command" != test && ( "$role" == '*' || "$scenario" == '*' ) ]]; then
  echo "--command requires both ROLE and SCENARIO" >&2
  exit 1
fi

export ANSIBLE_CONFIG=$(pwd)/src/commcare_cloud/ansible/ansible.cfg
export ANSIBLE_ROLES_PATH=$(pwd)/src/commcare_cloud/ansible/roles
export CCHQ_COLLECTIONS_PATH=$(python -c 'from commcare_cloud.environment.paths import ANSIBLE_COLLECTIONS_PATHS as p; print(p)')
export MOLECULE_GLOB="tests/molecule/$role.$scenario/molecule.yml"

# --all picks every scenario matched by MOLECULE_GLOB, but only test/destroy
# have that option. Other subcommands need a specific scenario name instead.
if [[ "$role" == '*' || "$scenario" == '*' ]]; then
  select_opts=(--all)
else
  select_opts=(--scenario-name "$role.$scenario")
fi

rc=0
molecule --base-config tests/molecule/lib/base.yml "$command" "${select_opts[@]}" ${opts[@]+"${opts[@]}"} ${extra[@]+"${extra[@]}"} || rc=$?
if [ "$rc" -ne 0 ]; then
  printf '\033[1;31mFAILED: molecule %s %s (exit %s)\033[0m\n' "$command" "$role.$scenario" "$rc" >&2
fi
exit "$rc"
