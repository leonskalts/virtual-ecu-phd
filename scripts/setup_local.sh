#!/usr/bin/env bash
set -euo pipefail

SCRIPT_DIR="$(cd "$(dirname "${BASH_SOURCE[0]}")" && pwd)"
PROJECT_ROOT="$(cd "${SCRIPT_DIR}/.." && pwd)"
VENV_DIR="${PROJECT_ROOT}/.venv"

cd "${PROJECT_ROOT}"

echo "Virtual ECU Research Explorer setup"
echo "Project root: ${PROJECT_ROOT}"

if ! command -v python3 >/dev/null 2>&1; then
  echo "Error: python3 is required. Install it with your system package manager." >&2
  exit 1
fi

if [ -d "${VENV_DIR}" ] && { [ ! -x "${VENV_DIR}/bin/python" ] || [ ! -f "${VENV_DIR}/bin/activate" ]; }; then
  echo "Removing incomplete virtual environment at .venv"
  rm -rf "${VENV_DIR}"
fi

if [ ! -d "${VENV_DIR}" ]; then
  echo "Creating local Python virtual environment at .venv"
  if ! python3 -m venv "${VENV_DIR}"; then
    rm -rf "${VENV_DIR}"
    echo
    echo "Error: could not create the Python virtual environment." >&2
    echo "On Ubuntu/WSL, install the venv prerequisite and rerun setup:" >&2
    echo "  sudo apt install -y python3-venv" >&2
    exit 1
  fi
else
  echo "Using existing Python virtual environment at .venv"
fi

# shellcheck disable=SC1091
source "${VENV_DIR}/bin/activate"

python -m pip install --upgrade pip
python -m pip install -r requirements.txt

echo "Building virtual_ecu simulator"
make

mkdir -p logs logs/gui_custom results presets

echo
echo "Setup complete."
echo "Launch the GUI with:"
echo "  bash scripts/launch_gui.sh"
echo
echo "Generated logs are written under logs/."
echo "Generated reports and figures are written under results/."
