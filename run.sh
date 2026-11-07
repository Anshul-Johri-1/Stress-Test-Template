#!/usr/bin/env bash
# Stress tester entry point. All logic lives in stress.py — see README.md or ./run.sh -h
ulimit -s unlimited 2>/dev/null || ulimit -s hard 2>/dev/null
exec python3 "$(dirname "$0")/stress.py" "$@"
