#!/bin/bash
set -e
set -x

rm -rf build dist
# Install required dependencies
uv pip install wheel twine protobuf

# First build the wheel
uv build --wheel

# Upload to PyPI
uv run twine upload dist/* --verbose
# echo Pushing git tags…
