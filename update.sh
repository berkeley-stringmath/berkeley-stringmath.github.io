#!/usr/bin/env bash
set -euo pipefail

if [ "$#" -gt 0 ]; then
  git add "$@"
else
  git add -A
fi
git commit -m "Update site"
git push origin main
