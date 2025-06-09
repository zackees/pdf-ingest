#!/usr/bin/env -S uv run --script

# /// script
# dependencies = [
#
# ]
# ///

import os

os.system('docker compose down --rmi=all')
os.system('docker compose up --build --no-start')

os.system('docker compose run --rm --service-ports --entrypoint /bin/bash app')