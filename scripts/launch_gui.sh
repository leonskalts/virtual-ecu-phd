#!/usr/bin/env bash
set -euo pipefail

SCRIPT_DIR="$(cd "$(dirname "${BASH_SOURCE[0]}")" && pwd)"
PROJECT_ROOT="$(cd "${SCRIPT_DIR}/.." && pwd)"
VENV_DIR="${PROJECT_ROOT}/.venv"

cd "${PROJECT_ROOT}"

if [ -d "${VENV_DIR}" ]; then
  # shellcheck disable=SC1091
  source "${VENV_DIR}/bin/activate"
fi

if [ ! -x "${PROJECT_ROOT}/virtual_ecu" ] && [ ! -x "${PROJECT_ROOT}/virtual_ecu.exe" ]; then
  echo "virtual_ecu executable not found; running make..."
  make
fi

if command -v python3 >/dev/null 2>&1; then
  PYTHON_BIN="python3"
elif command -v python >/dev/null 2>&1; then
  PYTHON_BIN="python"
else
  echo "Error: Python is required to launch the GUI." >&2
  exit 1
fi

exec "${PYTHON_BIN}" scripts/virtual_ecu_gui.py
