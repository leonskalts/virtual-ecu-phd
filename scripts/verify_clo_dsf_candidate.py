#!/usr/bin/env python3
"""Verify the frozen candidate before any future independent study."""
import hashlib
import json
from pathlib import Path
ROOT=Path(__file__).resolve().parents[1]
OUT=ROOT/'results/cross_layer_safety_v7_dev'

def verify():
    manifest=json.loads((OUT/'clo_dsf_candidate_hashes.json').read_text())
    for name,expected in manifest['sha256'].items():
        path=ROOT/name
        if not path.is_file() or hashlib.sha256(path.read_bytes()).hexdigest()!=expected:
            raise ValueError('Frozen CLO-DSF artifact changed: '+name)
    config=json.loads((OUT/'clo_dsf_candidate_config.json').read_text())['parameters']
    lines=(OUT/'clo_dsf_candidate.cfg').read_text().splitlines()
    runtime=dict(line.split('=',1) for line in lines if line and not line.startswith('#'))
    for name,value in config.items():
        if name=='conflict_rule':assert runtime[name]==value
        else:assert float(runtime[name])==value
    assert len(config)==len(runtime)
    return len(manifest['sha256'])
if __name__=='__main__':print('Frozen candidate verified:',verify(),'SHA-256 entries')
