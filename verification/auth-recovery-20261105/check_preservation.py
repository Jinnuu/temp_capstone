"""Inspect-only checks. Private baseline and account digest never enter Git."""
import json, subprocess, pathlib, hashlib
root=pathlib.Path('verification/auth-recovery-20261105')
private=pathlib.Path('.ui-preview/audit/auth-recovery')
baseline_count=json.loads((private/'account-state-summary-full.json').read_text())['users']
code='''import django; django.setup()
from django.contrib.auth import get_user_model
from django.conf import settings
from accounts import recovery
import json,hashlib
U=get_user_model()
rows=list(U.objects.order_by("pk").values("pk","username","password","email","is_active","is_staff","is_superuser","role"))
print(json.dumps({"digest":hashlib.sha256(json.dumps(rows[:BASELINE_COUNT],sort_keys=True).encode()).hexdigest(),"account_count":U.objects.count(),"additional_registrations":max(len(rows)-BASELINE_COUNT,0),"additional_active_accounts":sum(row["is_active"] for row in rows[BASELINE_COUNT:]),"email_missing":U.objects.filter(email="").count(),"delivery_mode":settings.ACCOUNT_RECOVERY_DELIVERY_MODE,"delivery_available":recovery.delivery_available(),"queue_length":recovery.store().llen(recovery.key("queue")),"auth_backends":settings.AUTHENTICATION_BACKENDS,"session_engine":settings.SESSION_ENGINE}))'''
code=code.replace('BASELINE_COUNT',str(baseline_count))
result=json.loads(subprocess.check_output(['docker','compose','-p','snp-ui-preview','--env-file','.ui-preview/compose.env','-f','compose.ui-preview.yml','exec','-T','web','python','-c',code]))
expected=json.loads((private/'requested-account-state.json').read_text())['existing_account_security_digest']
assert result.pop('digest')==expected
result['existing_account_credentials_roles_approval_email_unchanged']=True
before=json.loads((private/'containers-before.json').read_text())
changed=[]
for d in json.loads(subprocess.check_output(['docker','inspect',*[n.lstrip('/') for n in before]])):
    n=d['Name'];old=before[n]
    if n in ['/snp-ui-preview-web-1','/snp-ui-preview-proxy-1']:continue
    for k in ['Id','Image']:
        if d[k]!=old[k]:changed.append(n+':'+k)
    for k in ['Pid','StartedAt','Running']:
        if d['State'][k]!=old['State'][k]:changed.append(n+':'+k)
    if sorted(d['Mounts'],key=lambda m:m['Destination'])!=sorted(old['Mounts'],key=lambda m:m['Destination']):changed.append(n+':mounts')
    if d['NetworkSettings']['Networks']!=old['NetworkSettings']['Networks']:changed.append(n+':networks')
assert not changed,changed
result['unchanged_existing_containers_including_preview_db']=len(before)-2
result['protected_resource_changes']=changed
result['sprint_final_unchanged']=subprocess.check_output(['git','rev-parse','sprint-final']).decode().strip()=='133b950221bd9cc1effaa51539abf7f88bb095c1'
assert result['sprint_final_unchanged']
result['http_login_status']={str(port):int(subprocess.check_output(['curl','-s','--max-time','10','-o','/dev/null','-w','%{http_code}',f'http://127.0.0.1:{port}/accounts/login/']).decode()) for port in [8000,8007,8010,8011]}
assert all(v==200 for v in result['http_login_status'].values())
hashes=json.loads((private/'deployed-source-hashes.json').read_text())
assert all(hashlib.sha256(pathlib.Path(p).read_bytes()).hexdigest()==v for p,v in hashes.items())
result['deployed_auth_source_matches']=True
(root/'deployment-and-protection.json').write_text(json.dumps(result,indent=2))
print('Account/security state and protected services preserved; deployment matches source.')
