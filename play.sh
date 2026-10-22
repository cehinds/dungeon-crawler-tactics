#!/usr/bin/env sh
set -eu
cd "$(dirname "$0")"
python3 Tools/serve_game.py "$@"
