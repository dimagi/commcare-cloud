#!/bin/sh
# Fake git for git_setup_release. `clone` creates its destination dir, and
# `checkout`, which it runs in the new release, copies in the fixture tree.
# Any other command does nothing.
case "$1" in
  clone)
    eval dest=\${$#}
    mkdir -p "$dest"
    ;;
  checkout)
    cp -R /var/tmp/fake-commcare-hq/. .
    ;;
esac
