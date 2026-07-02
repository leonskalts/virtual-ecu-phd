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
git clone <repository-url> virtual-ecu-phd
cd virtual-ecu-phd
bash scripts/setup_local.sh
```

Launch the GUI:

```bash
bash scripts/launch_gui.sh
```

Generated simulator logs are saved under `logs/`. GUI exports, figures, and
study outputs are saved under `results/`.

## Windows

Recommended option: install WSL Ubuntu, clone the repository inside WSL, and
follow the Linux instructions above.

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
