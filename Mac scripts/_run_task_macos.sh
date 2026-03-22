#!/bin/bash
set -u

SCRIPT_REL="${1:-}"
TASK_LABEL="${2:-MRP Task}"

if [[ -z "$SCRIPT_REL" ]]; then
  echo "Missing task script path."
  exit 1
fi

SCRIPT_DIR="$(cd "$(dirname "${BASH_SOURCE[0]}")" && pwd)"
PROJECT_ROOT="$(cd "$SCRIPT_DIR/.." && pwd)"
PROJECT_PARENT="$(cd "$PROJECT_ROOT/.." && pwd)"
CACHE_DIR="$PROJECT_ROOT/cache"
mkdir -p "$CACHE_DIR"
export PYTHONPYCACHEPREFIX="$CACHE_DIR"

if [[ -n "${MRP_PYTHON:-}" ]]; then
  VENV_PYTHON="$MRP_PYTHON"
elif [[ -x "$PROJECT_PARENT/.venv-experiment310/bin/python" ]]; then
  VENV_PYTHON="$PROJECT_PARENT/.venv-experiment310/bin/python"
elif [[ -x "$PROJECT_ROOT/.venv-experiment310/bin/python" ]]; then
  VENV_PYTHON="$PROJECT_ROOT/.venv-experiment310/bin/python"
else
  VENV_PYTHON=""
fi

SCRIPT_PATH="$PROJECT_ROOT/$SCRIPT_REL"

if [[ ! -f "$SCRIPT_PATH" ]]; then
  echo "Could not find task script:"
  echo "  $SCRIPT_PATH"
  read -r -p "Press Enter to close..."
  exit 1
fi

if [[ -z "$VENV_PYTHON" || ! -x "$VENV_PYTHON" ]]; then
  echo "Could not find the experiment Python interpreter."
  echo
  echo "Checked:"
  echo "  $PROJECT_PARENT/.venv-experiment310/bin/python"
  echo "  $PROJECT_ROOT/.venv-experiment310/bin/python"
  echo
  echo "Fix one of these first:"
  echo "  1. Create the dedicated project environment"
  echo "  2. Or set MRP_PYTHON to the PsychoPy/experiment python path"
  read -r -p "Press Enter to close..."
  exit 1
fi

cd "$PROJECT_ROOT" || exit 1

echo "Launching $TASK_LABEL..."
echo "Python: $VENV_PYTHON"
echo "Script: $SCRIPT_PATH"
echo

"$VENV_PYTHON" "$SCRIPT_PATH"
EXIT_CODE=$?

if [[ "$EXIT_CODE" -ne 0 ]]; then
  echo
  echo "$TASK_LABEL exited with code $EXIT_CODE."
  read -r -p "Press Enter to close..."
fi

exit "$EXIT_CODE"
