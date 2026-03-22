#!/usr/bin/env bash
set -euo pipefail

ROOT_DIR="$(cd "$(dirname "${BASH_SOURCE[0]}")" && pwd)"
PROJECT_PARENT="$(cd "$ROOT_DIR/.." && pwd)"
VENV_PATH="${1:-$PROJECT_PARENT/.venv-experiment310}"

if [[ -z "${PYTHON_BIN:-}" ]]; then
  if command -v python3.10 >/dev/null 2>&1; then
    PYTHON_BIN="$(command -v python3.10)"
  elif [[ -x "/opt/homebrew/bin/python3.10" ]]; then
    PYTHON_BIN="/opt/homebrew/bin/python3.10"
  elif [[ -x "/usr/local/bin/python3.10" ]]; then
    PYTHON_BIN="/usr/local/bin/python3.10"
  else
    PYTHON_BIN=""
  fi
fi

if [[ ! -x "$PYTHON_BIN" ]]; then
  echo "Python 3.10 was not found at: $PYTHON_BIN" >&2
  echo "Install it first, for example on macOS with: brew install python@3.10" >&2
  exit 1
fi

"$PYTHON_BIN" -m venv "$VENV_PATH"
"$VENV_PATH/bin/python" -m pip install --upgrade pip
"$VENV_PATH/bin/pip" install -r "$ROOT_DIR/requirements-experiment.txt"
"$VENV_PATH/bin/python" "$ROOT_DIR/Verification scripts/check_experiment_env.py"

cat <<EOF

Experiment environment ready.
Venv: $VENV_PATH

Activate it with:
  source "$VENV_PATH/bin/activate"

Run tasks with:
  "$VENV_PATH/bin/python" "$ROOT_DIR/Implicit Association Task/IAT Task Script/iat_practice.py"
  "$VENV_PATH/bin/python" "$ROOT_DIR/Implicit Association Task/IAT Task Script/iat_main.py"
  "$VENV_PATH/bin/python" "$ROOT_DIR/Approach Avoidance Task/AAT Task Script/aat_practice.py"
  "$VENV_PATH/bin/python" "$ROOT_DIR/Approach Avoidance Task/AAT Task Script/aat_main.py"
EOF
