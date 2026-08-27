#!/bin/bash
# FRIDAY Launcher - activates venv and starts assistant
cd "$(dirname "$0")"
source venv/bin/activate
python main.py "$@"
