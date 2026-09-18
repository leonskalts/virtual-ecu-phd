#!/usr/bin/env python3
"""Additive launcher; historical GUI and its hashed source remain unchanged."""
import virtual_ecu_gui as gui
from virtual_ecu.clo_dsf_final_gui import install
install()
if __name__=='__main__':gui.main()
