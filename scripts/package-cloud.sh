#!/usr/bin/env bash
# Offline packaging only: no AWS deployment or API calls.
set -euo pipefail
cd "$(dirname "$0")/.."
task_package=$(mktemp -d)
uv export --frozen --no-dev --extra cloud --no-emit-project --output-file "$task_package/requirements.txt" > /dev/null
uv pip install --python-platform aarch64-manylinux2014 --python-version 3.12 --only-binary=:all: --target "$task_package/package" -r "$task_package/requirements.txt"
mkdir -p "$task_package/package/backend" "$task_package/package/infra" output
cp backend/*.py "$task_package/package/backend/"
cp infra/*.py "$task_package/package/infra/"
cp agentcore_entry.py "$task_package/package/"
if [ -e output/cloud-package ]; then
  echo 'output/cloud-package already exists. Move it aside before rebuilding.'
  exit 1
fi
mv "$task_package/package" output/cloud-package
(cd output/cloud-package && zip -q -r ../neighborgear-agent.zip .)
echo 'Created output/cloud-package and output/neighborgear-agent.zip. Nothing deployed.'
