#!/usr/bin/env bash
set -euo pipefail
cd "$(dirname "${BASH_SOURCE[0]}")"

usage() {
  echo "Scaffold a new molecule scenario at tests/molecule/<role>-<scenario>/"
  echo ""
  echo "Usage: init.sh ROLE [SCENARIO]"
}

for arg in "$@"; do
  case "$arg" in
    -h|--help)
      usage
      exit 0
      ;;
  esac
done

if [ "$#" -lt 1 ] || [ "$#" -gt 2 ]; then
  usage >&2
  exit 1
fi
role=$1
scenario=${2:-default}
target="$role-$scenario"

if [ -e "$target" ]; then
  echo "tests/molecule/$target already exists" >&2
  exit 1
fi

mkdir "$role"
cd "$role"

# A non-default scenario is refused unless ./molecule/default already
# exists. Satisfy it with a placeholder.
[ "$scenario" = default ] || mkdir -p molecule/default

molecule init scenario -d containers "$scenario"

cd ..
mv "$role/molecule/$scenario" "$target"
rm -rfv "$role"

echo
echo "Initialized scenario: tests/molecule/$target"
