#!/usr/bin/env bash
set -euo pipefail

APP_NAME="Virtual ECU"
SCRIPT_DIR="$(cd "$(dirname "${BASH_SOURCE[0]}")" && pwd)"
PROJECT_ROOT="$(cd "${SCRIPT_DIR}/.." && pwd)"
LAUNCHER="${PROJECT_ROOT}/scripts/launch_gui.sh"
PNG_ICON="${PROJECT_ROOT}/assets/fault_path/Virtual_ECU.png"
ICON_DIR="${PROJECT_ROOT}/.shortcut"
ICO_ICON="${ICON_DIR}/Virtual_ECU.ico"
POWERSHELL_LAUNCHER="${ICON_DIR}/Launch_Virtual_ECU.ps1"

cd "${PROJECT_ROOT}"

usage() {
  cat <<USAGE
Usage: bash scripts/create_desktop_shortcut.sh [--linux]

Creates a desktop/application shortcut for Virtual ECU.
Default behavior under WSL creates a Windows desktop shortcut.
Use --linux to create a Linux .desktop launcher instead.
USAGE
}

for arg in "$@"; do
  case "${arg}" in
    --linux)
      CREATE_LINUX=1
      ;;
    -h|--help)
      usage
      exit 0
      ;;
    *)
      echo "Unknown option: ${arg}" >&2
      usage >&2
      exit 1
      ;;
  esac
done

if [ ! -f "${LAUNCHER}" ]; then
  echo "Error: scripts/launch_gui.sh was not found." >&2
  exit 1
fi

if ! bash -n "${LAUNCHER}"; then
  echo "Error: scripts/launch_gui.sh has a shell syntax problem." >&2
  exit 1
fi

if [ ! -x "${LAUNCHER}" ]; then
  chmod +x "${LAUNCHER}"
fi

python_for_icon() {
  if [ -x "${PROJECT_ROOT}/.venv/bin/python" ]; then
    printf "%s\n" "${PROJECT_ROOT}/.venv/bin/python"
  elif command -v python3 >/dev/null 2>&1; then
    command -v python3
  elif command -v python >/dev/null 2>&1; then
    command -v python
  else
    return 1
  fi
}

prepare_icon() {
  if [ -f "${ICO_ICON}" ]; then
    printf "%s\n" "${ICO_ICON}"
    return 0
  fi

  if [ ! -f "${PNG_ICON}" ]; then
    echo "Icon source not found; shortcut will use the default WSL icon." >&2
    return 1
  fi

  local python_bin
  if ! python_bin="$(python_for_icon)"; then
    echo "Python not found for icon conversion; shortcut will use the default WSL icon." >&2
    return 1
  fi

  mkdir -p "${ICON_DIR}"
  if "${python_bin}" - "${PNG_ICON}" "${ICO_ICON}" <<'PY'
import sys
from pathlib import Path

source = Path(sys.argv[1])
target = Path(sys.argv[2])

try:
    from PIL import Image
except Exception as exc:
    print(f"Pillow unavailable: {exc}", file=sys.stderr)
    raise SystemExit(1)

target.parent.mkdir(parents=True, exist_ok=True)
with Image.open(source) as image:
    image.save(target, format="ICO", sizes=[(16, 16), (32, 32), (48, 48), (64, 64), (128, 128), (256, 256)])
PY
  then
    printf "%s\n" "${ICO_ICON}"
    return 0
  fi

  rm -f "${ICO_ICON}"
  echo "Icon conversion failed; shortcut will use the default WSL icon." >&2
  return 1
}

ps_quote() {
  local value escaped
  value="$1"
  escaped="$(printf "%s" "${value}" | sed "s/'/''/g")"
  printf "'%s'" "${escaped}"
}

write_powershell_launcher() {
  mkdir -p "${ICON_DIR}"

  local distro_line=""
  if [ -n "${WSL_DISTRO_NAME:-}" ]; then
    distro_line="    \"-d\", $(ps_quote "${WSL_DISTRO_NAME}"),"
  fi

  cat > "${POWERSHELL_LAUNCHER}" <<PS1
\$ErrorActionPreference = "Continue"
\$Host.UI.RawUI.WindowTitle = "Virtual ECU"

\$wslExe = Join-Path \$env:SystemRoot "System32\\wsl.exe"
\$wslArgs = @(
${distro_line}
    "--cd", $(ps_quote "${PROJECT_ROOT}"),
    "bash", "-lc", $(ps_quote "bash scripts/launch_gui.sh; code=\$?; echo EXIT_CODE:\$code; if [ \$code -ne 0 ]; then read -p 'Press Enter to close...'; fi; exit \$code")
)

Write-Host "Launching Virtual ECU Research Explorer..."
Write-Host "Project root: ${PROJECT_ROOT}"
Write-Host ""

& \$wslExe @wslArgs
\$exitCode = \$LASTEXITCODE

Write-Host ""
Write-Host "EXIT_CODE:\$exitCode"
if (\$exitCode -ne 0) {
    Read-Host "Press Enter to close"
}
PS1
}

create_windows_shortcut() {
  if ! command -v powershell.exe >/dev/null 2>&1; then
    echo "powershell.exe was not found. Run this from WSL on Windows, or use --linux for a Linux desktop entry." >&2
    return 1
  fi

  if ! command -v wslpath >/dev/null 2>&1; then
    echo "wslpath was not found. This shortcut creator is intended for WSL." >&2
    return 1
  fi

  local icon_path="" icon_path_win="" launcher_win ps_script ps_script_win
  if icon_path="$(prepare_icon)"; then
    icon_path_win="$(wslpath -w "${icon_path}")"
  fi

  write_powershell_launcher
  launcher_win="$(wslpath -w "${POWERSHELL_LAUNCHER}")"

  ps_script="$(mktemp --suffix=.ps1)"
  cat > "${ps_script}" <<'PS1'
param(
    [Parameter(Mandatory=$true)]
    [string]$ShortcutName,

    [Parameter(Mandatory=$true)]
    [string]$LauncherScript,

    [string]$PngSource = "",

    [string]$WslIconPath = "",

    [string]$IconSourcePath = ""
)

$ErrorActionPreference = "Stop"

$desktopPath = [Environment]::GetFolderPath("Desktop")
if (-not $desktopPath) {
    throw "Could not determine the Windows Desktop folder."
}

$shortcutPath = Join-Path $desktopPath "$ShortcutName.lnk"
$windowsIconPath = ""
if ($IconSourcePath -and (Test-Path $IconSourcePath)) {
    $windowsIconDir = Join-Path $env:LOCALAPPDATA "VirtualECU"
    New-Item -ItemType Directory -Path $windowsIconDir -Force | Out-Null
    $windowsIconPath = Join-Path $windowsIconDir "Virtual_ECU_shortcut.ico"
    Copy-Item -Path $IconSourcePath -Destination $windowsIconPath -Force
}

$shell = New-Object -ComObject WScript.Shell
$shortcut = $shell.CreateShortcut($shortcutPath)
$shortcut.TargetPath = "C:\Windows\System32\WindowsPowerShell\v1.0\powershell.exe"
$shortcut.Arguments = "-NoExit -ExecutionPolicy Bypass -File `"$LauncherScript`""
$shortcut.WorkingDirectory = [Environment]::GetFolderPath("Desktop")
$shortcut.Description = "Launch Virtual ECU Research Explorer"
if ($windowsIconPath -and (Test-Path $windowsIconPath)) {
    $shortcut.IconLocation = "$windowsIconPath,0"
}
$shortcut.Save()

if (-not (Test-Path $shortcutPath)) {
    throw "Shortcut was not created at: $shortcutPath"
}

$shortcutReadback = $shell.CreateShortcut($shortcutPath)
Write-Output "PNG source: $PngSource"
if ($WslIconPath) {
    Write-Output "WSL ICO: $WslIconPath"
} else {
    Write-Output "WSL ICO: unavailable"
}
if ($windowsIconPath) {
    Write-Output "Windows ICO: $windowsIconPath"
} else {
    Write-Output "Windows ICO: unavailable"
}
Write-Output "Shortcut: $shortcutPath"
Write-Output "Target: $($shortcut.TargetPath)"
Write-Output "Arguments: $($shortcut.Arguments)"
if ($shortcutReadback.IconLocation) {
    Write-Output "IconLocation readback: $($shortcutReadback.IconLocation)"
} else {
    Write-Output "IconLocation readback: default"
}
PS1

  ps_script_win="$(wslpath -w "${ps_script}")"
  powershell.exe -NoProfile -ExecutionPolicy Bypass -File "${ps_script_win}" \
    -ShortcutName "${APP_NAME}" \
    -LauncherScript "${launcher_win}" \
    -PngSource "${PNG_ICON}" \
    -WslIconPath "${icon_path}" \
    -IconSourcePath "${icon_path_win}"
  rm -f "${ps_script}"
}

create_linux_shortcut() {
  local app_dir="${HOME}/.local/share/applications"
  local desktop_dir="${HOME}/Desktop"
  local desktop_file="${app_dir}/virtual-ecu.desktop"
  local desktop_copy="${desktop_dir}/${APP_NAME}.desktop"
  local icon_path="${PNG_ICON}"

  mkdir -p "${app_dir}"
  cat > "${desktop_file}" <<DESKTOP
[Desktop Entry]
Type=Application
Name=${APP_NAME}
Comment=Launch Virtual ECU Research Explorer
Exec=bash "${LAUNCHER}"
Icon=${icon_path}
Terminal=false
Categories=Education;Science;
DESKTOP
  chmod +x "${desktop_file}"

  echo "Linux application shortcut created at: ${desktop_file}"
  if [ -d "${desktop_dir}" ]; then
    cp "${desktop_file}" "${desktop_copy}"
    chmod +x "${desktop_copy}"
    echo "Desktop shortcut copied to: ${desktop_copy}"
  fi
}

echo "Virtual ECU shortcut creator"
echo "Project root: ${PROJECT_ROOT}"

if [ "${CREATE_LINUX:-0}" = "1" ]; then
  create_linux_shortcut
else
  create_windows_shortcut
fi

echo
echo "Shortcut creation complete."
echo "If you move this project folder, rerun this script so the shortcut points to the new location."
