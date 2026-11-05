import hashlib, json, pathlib, subprocess
changed=set(subprocess.check_output(['git','diff','--name-only']).decode().splitlines())
changed.update(subprocess.check_output(['git','ls-files','--others','--exclude-standard']).decode().splitlines())
files=sorted(p for p in changed if p.startswith(('accounts/','config/','procurement/','templates/')) and p.endswith(('.py','.html')))
code='import hashlib,json;from pathlib import Path;print(json.dumps({p:hashlib.sha256(Path(p).read_bytes()).hexdigest() for p in '+repr(files)+'}))'
compose=['docker','compose','-p','snp-ui-preview','--env-file','.ui-preview/compose.env','-f','compose.ui-preview.yml']
deployed=json.loads(subprocess.check_output(compose+['exec','-T','web','python','-B','-c',code]))
assert all(hashlib.sha256(pathlib.Path(path).read_bytes()).hexdigest()==digest for path,digest in deployed.items())
pathlib.Path('verification/rbac-20261105/deployed-source.json').write_text(json.dumps({'allMatch':True,'files':files},indent=2))
print('Changed application sources match the deployed Preview image.')
