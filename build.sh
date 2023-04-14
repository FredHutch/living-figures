#!/bin/bash

set -e

# Set up a virtual environment
[ ! -d .venv ] && python3 -m venv .venv
source .venv/bin/activate

# Install requirements
python3 -m pip install -r requirements.txt
python3 -m pip install -e ./


find hugo/content/post -name build.py | xargs python3
