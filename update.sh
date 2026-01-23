#!/usr/bin/env bash
set -euo pipefail

git add -A
git commit -m "Update site"
git push origin main
