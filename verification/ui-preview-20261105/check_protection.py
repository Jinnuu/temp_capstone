"""Compare inspect-only local audit; never read operational DB contents or secrets."""
import subprocess,json,pathlib,hashlib,urllib.request
r=pathlib.Path('verification/ui-preview-20261105');p=pathlib.Path('.ui-preview/audit')
old=json.loads((p/'existing-before.json').read_text())
current=json.loads(subprocess.check_output(['docker','inspect',*old.keys()]));changed=[]
for d in current:
    name=d['Name'].lstrip('/');o=old[name]
    for k in ['Id','Image']:
        if o[k]!=d[k]:changed.append(name+':'+k)
    # Docker does not promise mount array order.
    if sorted(o['Mounts'],key=lambda x:x['Destination'])!=sorted(d['Mounts'],key=lambda x:x['Destination']):changed.append(name+':Mounts')
    for k in ['StartedAt','Pid','Running']:
        if o['State'][k]!=d['State'][k]:changed.append(name+':State.'+k)
    if o['NetworkSettings']['Networks']!=d['NetworkSettings']['Networks']:changed.append(name+':networks')
assert not changed,changed
new=json.loads(subprocess.check_output(['docker','inspect','snp-ui-preview-db-1','snp-ui-preview-web-1','snp-ui-preview-proxy-1']))
for d in new:
    assert d['State']['Running'] and d['State']['Health']['Status']=='healthy'
    expected=json.loads(subprocess.check_output(['docker','image','inspect',d['Config']['Image']]))[0]['Id']
    assert d['Image']==expected
prior_vols=[json.loads(x)['Name'] for x in (p/'volume-inventory-before.jsonl').read_text().splitlines()]
prior_nets=[json.loads(x)['Name'] for x in (p/'network-inventory-before.jsonl').read_text().splitlines()]
assert all(m.get('Name') not in prior_vols for d in new for m in d['Mounts'] if m['Type']=='volume')
assert all(n not in prior_nets for d in new for n in d['NetworkSettings']['Networks'])
payload=urllib.request.urlopen('http://127.0.0.1:8011/static/ui/build/snp-ui.js',timeout=10).read()
assert hashlib.sha256(payload).hexdigest()==hashlib.sha256(pathlib.Path('static/ui/build/snp-ui.js').read_bytes()).hexdigest()
health={url:urllib.request.urlopen(url,timeout=10).status for url in ['http://127.0.0.1:8000/accounts/login/','http://127.0.0.1:8007/accounts/login/','http://127.0.0.1:8011/accounts/login/','http://100.65.149.96:8011/accounts/login/']}
images=json.loads((r/'image-content.json').read_text())
assert all(hashlib.sha256((pathlib.Path('ml_models')/f).read_bytes()).hexdigest()==h for f,h in images['models'].items())
stable=subprocess.check_output(['git','rev-parse','sprint-final']).decode().strip()
remote=subprocess.check_output(['git','ls-remote','--heads','origin','sprint-final']).decode().split()[0]
assert stable==remote=='133b950221bd9cc1effaa51539abf7f88bb095c1'
out={'passed':True,'existing_containers_compared':len(old),'changed_existing_resources':changed,'no_existing_network_or_volume_attached':True,'sprint_final_local_and_remote':stable,'model_file_hashes_unchanged':True,'http_status':health,'preview':[{ 'name':d['Name'].strip('/'),'image_id':d['Image'],'health':d['State']['Health']['Status'],'networks':list(d['NetworkSettings']['Networks']),'volumes':[m.get('Name') for m in d['Mounts'] if m['Type']=='volume']} for d in new]}
(r/'protection-final.json').write_text(json.dumps(out,indent=2))
print('Protected resources unchanged; all four HTTP probes returned 200.')
