"""Emit a reproducible package/model manifest without deployment credentials."""
import hashlib
import importlib.metadata
import json
import platform
from pathlib import Path

root=Path(__file__).resolve().parent.parent
packages={}
for line in (root/'requirements.txt').read_text().splitlines():
    if '==' not in line:
        continue
    name,expected=line.split('==',1)
    try:
        actual=importlib.metadata.version(name)
    except importlib.metadata.PackageNotFoundError:
        actual=None
    packages[name]={'expected':expected,'actual':actual,'matches':actual==expected}
print(json.dumps({'python':platform.python_version(),'packages':packages,'model_sha256':{
    p.name:hashlib.sha256(p.read_bytes()).hexdigest() for p in (root/'ml_models').glob('*.pkl')
}},indent=2))
