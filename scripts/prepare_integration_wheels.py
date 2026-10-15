"""Download only XLS runtime/test wheels, verifying PyPI's SHA-256 metadata."""
import hashlib
import json
from pathlib import Path
import urllib.request

out=Path('/tmp/sprint7-test-wheels')
out.mkdir(exist_ok=True)
for name,version in [('xlrd','2.0.2'),('xlwt','1.3.0')]:
    with urllib.request.urlopen(f'https://pypi.org/pypi/{name}/{version}/json', timeout=30) as response:
        metadata=json.load(response)
    wheel=next(item for item in metadata['urls'] if item['filename'].endswith('.whl'))
    with urllib.request.urlopen(wheel['url'], timeout=30) as response:
        content=response.read()
    assert hashlib.sha256(content).hexdigest()==wheel['digests']['sha256']
    (out/wheel['filename']).write_bytes(content)
    print(wheel['filename'])
