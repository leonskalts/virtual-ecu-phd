# Installation

This project is path-independent. You can clone or copy it to any folder and
use the setup and launcher scripts without editing hardcoded paths.

## Recommended: WSL or Linux

Install system prerequisites:

```bash
sudo apt update
sudo apt install -y git build-essential python3 python3-venv python3-pip
```

Clone and set up the project:

```bash
git clone https://github.com/leonskalts/virtual-ecu-phd.git virtual-ecu-phd
cd virtual-ecu-phd
bash scripts/setup_local.sh
```

Launch the GUI:

```bash
bash scripts/launch_gui.sh
```

On Windows 11 with WSLg, the GUI should open directly from WSL. On older WSL
setups, a separate X server may be required for graphical applications.

Generated simulator logs are saved under `logs/`. GUI exports, figures, and
study outputs are saved under `results/`.

## Optional RTL / Security Study Support

Verilator is **not required** for the standard Virtual ECU simulator or GUI. It
is needed only when generating traces for the optional RTL Hardware Trojan
security study.

Install Verilator on Ubuntu/WSL:

```bash
sudo apt install -y verilator
```

Run the HT1–HT4 RTL study from the repository root:

```bash
make rtl-trojan-study
```

Generated study evidence is written under:

```text
results/rtl_hardware_trojan_study_v1/
```

## Desktop Shortcut

After running `bash scripts/setup_local.sh`, create a desktop shortcut with:

```bash
bash scripts/create_desktop_shortcut.sh
```

On Windows with WSL, this creates a Windows desktop shortcut named
`Virtual ECU`. Double-clicking it launches the GUI through WSL using
`scripts/launch_gui.sh`; it does not open VS Code or the project folder.

The script tries to convert `assets/fault_path/Virtual_ECU.png` into a local
shortcut icon. If icon creation fails, the shortcut is still created with the
default WSL icon. The shortcut is specific to the current clone location, so if
you move the project folder, rerun `bash scripts/create_desktop_shortcut.sh`.

On Linux desktops, you can create a `.desktop` launcher with:

```bash
bash scripts/create_desktop_shortcut.sh --linux
```

## Windows

Recommended option: install WSL Ubuntu, clone the repository inside WSL, and
follow the WSL/Linux instructions above. Windows 11 users normally receive GUI
support through WSLg; older WSL installations may require a separate X server.

Optional native Windows launcher:

```bat
scripts\launch_gui.bat
```

Native Windows usage requires Python. If the simulator executable is not
already built, native Windows also requires a compatible C build environment and
`make`. If that is not already configured, use WSL Ubuntu for the simplest
setup.

## Manual Launch

After setup, the GUI can also be launched manually from the repository root:

```bash
source .venv/bin/activate
python3 scripts/virtual_ecu_gui.py
```
