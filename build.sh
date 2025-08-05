#!/usr/bin/env bash
# exit on error
set -o errexit

pip install -r requirements.txt

export PLAYWRIGHT_BROWSERS_PATH=./pw-browsers

playwright install chromium
