#!/bin/bash
cd "$(dirname "$0")" || exit 1
bash ./expedition-update.sh "$@"
result=$?
printf '\nPress Return to close...'
read -r _unused
exit "$result"
