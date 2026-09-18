#!/usr/bin/env python3
"""Exercise the unchanged legacy desktop checks through the additive final GUI."""
from pathlib import Path
import os
import sys
import tempfile
from unittest.mock import patch

ROOT = Path(__file__).resolve().parents[1]
sys.path[:0] = [str(ROOT / 'scripts'), str(ROOT / 'tests'), str(ROOT / 'python')]
expand = os.path.expanduser
with tempfile.TemporaryDirectory(prefix='clo-final-legacy-fonts-') as fonts:
    with patch('os.path.expanduser', side_effect=lambda p: fonts if p == '~/.fonts/' else expand(p)):
        import virtual_ecu_final_gui
    original = ROOT / 'tests/gui_v62_desktop_checks.py'
    source = original.read_text().replace(
        "OUT=ROOT/'results/cross_layer_safety_v6_2/validation'",
        "OUT=ROOT/'results/cross_layer_safety_v7_2_confirmation/validation/gui_legacy'",
    )
    exec(compile(source, str(original), 'exec'), {'__file__': str(original), '__name__': '__main__'})
