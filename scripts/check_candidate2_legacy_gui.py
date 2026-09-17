#!/usr/bin/env python3
"""Run unchanged legacy GUI checks with all generated output relocated."""
from pathlib import Path
import os,sys,tempfile
from unittest.mock import patch
ROOT=Path(__file__).resolve().parents[1]
sys.path[:0]=[str(ROOT/'scripts'),str(ROOT/'tests'),str(ROOT/'python')]
fonts=Path(tempfile.mkdtemp(prefix='candidate2-legacy-fonts-'));expand=os.path.expanduser
with patch('os.path.expanduser',side_effect=lambda p:str(fonts) if p=='~/.fonts/' else expand(p)):
 import virtual_ecu_gui
original=ROOT/'tests/gui_v62_desktop_checks.py'
source=original.read_text().replace("OUT=ROOT/'results/cross_layer_safety_v6_2/validation'","OUT=ROOT/'results/cross_layer_safety_v7_1_dev/validation/gui_legacy'")
exec(compile(source,str(original),'exec'),{'__file__':str(original),'__name__':'__main__'})
