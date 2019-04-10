#!/usr/bin/env bash

ERROR_MESSAGE="$1"

git diff
git update-index -q --refresh
if git diff-index --quiet HEAD --; then
    # No changes
    exit 0
else
    # Changes
    echo "${ERROR_MESSAGE}"
    exit 1
fi
