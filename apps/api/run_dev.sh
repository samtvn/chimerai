#!/usr/bin/env bash
# Run the FastAPI dev server with correct PYTHONPATH
cd "$(dirname "$0")"
export PYTHONPATH="$(pwd)/../.."
exec uv run python -m uvicorn main:app --reload --host 0.0.0.0 "$@"
