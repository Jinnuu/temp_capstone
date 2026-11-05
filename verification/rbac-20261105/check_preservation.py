"""Private identity comparisons; public output contains no credentials or emails."""
import json, subprocess, pathlib, hashlib
root=pathlib.Path('verification/rbac-20261105')
private=pathlib.Path('.ui-preview/audit/rbac-20261105')
compose=['docker','compose','-p','snp-ui-preview','--env-file','.ui-preview/compose.env','-f','compose.ui-preview.yml']
identity=subprocess.check_output(compose+['exec','-T','web','python','-B','-c',
    'import django,json;django.setup();from accounts.models import User;print(json.dumps(list(User.objects.order_by("pk").values("pk","username","password","email","role","is_staff","is_superuser")),sort_keys=True))'])
expected=json.loads((private/'identity-before.json').read_text())
actual=json.loads(identity)
baseline_ids={row['pk'] for row in expected}
assert expected==[row for row in actual if row['pk'] in baseline_ids], 'Existing identity fields changed unexpectedly'
new_accounts=[row for row in actual if row['pk'] not in baseline_ids]
assert all(not row['is_staff'] and not row['is_superuser'] and row['role']=='NUTRITIONIST' for row in new_accounts)
code='''import django,json;django.setup()
from accounts.models import User,AccessAudit
from accounts.rbac import account_can_login,approval_mode
from accounts import recovery
rows=list(User.objects.order_by('pk').values('pk','is_active','account_state'))
print(json.dumps({'accounts':rows,'mode':approval_mode(),'deliveryMode':recovery.delivery_mode(),'targetEligible':[account_can_login(u) for u in User.objects.filter(username__in=['wlsdngur12','swwlsdngur12'])],'targetApprovalEvents':AccessAudit.objects.filter(action='account.approved_or_restored',target__username__in=['wlsdngur12','swwlsdngur12']).count(),'approvalAuditExists':AccessAudit.objects.filter(reason='operator_confirmed_preview_signup').exists()}))'''
# Delivery mode is read from settings, avoiding any SMTP operation.
code=code.replace('recovery.delivery_mode()',"__import__('django.conf',fromlist=['settings']).settings.ACCOUNT_RECOVERY_DELIVERY_MODE")
result=json.loads(subprocess.check_output(compose+['exec','-T','web','python','-B','-c',code]))
before=json.loads((private/'accounts-before.json').read_text())
old_active=set(before['active_ids']);target_ids={item['pk'] for item in before['targets']}
assert {r['pk'] for r in result['accounts'] if r['is_active'] and r['pk'] in baseline_ids} == old_active|target_ids
assert all(r['account_state']=='ACTIVE' for r in result['accounts'] if r['pk'] in target_ids)
assert all(r['account_state']=='LEGACY_INACTIVE' for r in result['accounts'] if r['pk'] in baseline_ids - (old_active|target_ids))
assert result['targetEligible']==[True,True]
assert result['targetApprovalEvents']==2
result.pop('accounts')
result.update({'existingAccountCount':len(expected),'newExternalRegistrationsDuringTask':len(new_accounts),'newAccountsWithoutPrivilegedFlags':True,'identityPasswordEmailLegacyRoleFlagsUnchanged':True,'activatedConfirmedPendingAccounts':2,'otherInactiveAccountsPreserved':True,'realTargetPasswordsNotRequestedOrTested':True})
baseline=json.loads((private/'containers-before.json').read_text())
protected=['/my-capstone','/my-capstone-sprint7','/snp-presentation','/snp-ui-preview-db-1','/snp-ui-preview-recovery-cache-1']
for name in protected:
    old=baseline[name]
    current=json.loads(subprocess.check_output(['docker','inspect',name.lstrip('/')]))[0]
    for key in ('Id','Image'):
        assert old[key]==current[key], (name,key)
    assert sorted(old['Mounts'],key=lambda item:item['Destination'])==sorted(current['Mounts'],key=lambda item:item['Destination']), (name,'Mounts')
    for key in ('Pid','StartedAt','Running'):
        assert old['State'][key]==current['State'][key],(name,key)
    assert old['NetworkSettings']['Networks']==current['NetworkSettings']['Networks']
result['protectedContainersUnchanged']=[x.lstrip('/') for x in protected]
result['sprintFinalUnchanged']=subprocess.check_output(['git','rev-parse','sprint-final']).decode().strip()=='133b950221bd9cc1effaa51539abf7f88bb095c1'
assert result['sprintFinalUnchanged']
result['httpLoginStatus']={str(port):int(subprocess.check_output(['curl','-s','--max-time','15','-o','/dev/null','-w','%{http_code}',f'http://127.0.0.1:{port}/accounts/login/'])) for port in (8000,8007,8010,8011)}
assert all(v==200 for v in result['httpLoginStatus'].values())
result['previewServices']=[json.loads(line) for line in subprocess.check_output(compose+['ps','--format','json']).decode().splitlines()]
result['previewServices']=[{'service':row['Service'],'state':row['State'],'health':row.get('Health')} for row in result['previewServices']]
assert len(result['previewServices'])==5 and all(row['health']=='healthy' for row in result['previewServices'])
(root/'deployment-and-protection.json').write_text(json.dumps(result,ensure_ascii=False,indent=2))
print('Identity fields, non-target states, protected services and stable branch verified.')
