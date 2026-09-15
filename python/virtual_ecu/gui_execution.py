"""Verify original command, loader, export and analysis functions after UI edits."""
import ast
import hashlib
import json
from pathlib import Path


def verify_gui_execution(root):
    lock=json.loads(Path(__file__).with_name('gui_execution_lock.json').read_text())
    tree=ast.parse((Path(root)/'scripts/virtual_ecu_gui.py').read_text())
    definitions={node.name:node for node in tree.body if isinstance(node,ast.FunctionDef)}
    gui=next(node for node in tree.body if isinstance(node,ast.ClassDef) and node.name=='VirtualECUGui')
    definitions.update({'VirtualECUGui.'+node.name:node for node in gui.body if isinstance(node,ast.FunctionDef)})
    for name,digest in lock['protected_definitions'].items():
        node=definitions.get(name)
        if node is None or hashlib.sha256(ast.dump(node).encode()).hexdigest()!=digest:
            raise ValueError('Frozen GUI execution/analysis definition changed: '+name)
    return len(lock['protected_definitions'])
