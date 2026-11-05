import json,subprocess,pathlib,hashlib
root=pathlib.Path('verification/fresh-portal-20261105');private=pathlib.Path('.ui-preview/audit/fresh-portal-20261105')
compose=['docker','compose','-p','snp-ui-preview','--env-file','.ui-preview/compose.env','-f','compose.ui-preview.yml']
code='''import django,json;django.setup()
from accounts.models import User
from accounts.rbac import is_main
from django.conf import settings
from accounts.supplier_identity import eligible_order_accounts
from procurement.models import PurchaseOrder
from inventory.models import Ingredient,SupplySpecification
bad=User.objects.exclude(pk__in=eligible_order_accounts()).values_list('pk',flat=True)
bad_counts={'orders':PurchaseOrder.objects.filter(supplier_id__in=bad).count(),'ingredients':Ingredient.objects.filter(supplier_id__in=bad).count(),'specifications':SupplySpecification.objects.filter(supplier_id__in=bad).count()}
assert not any(bad_counts.values()),'Noncanonical supplier references require review'
rows=list(User.objects.order_by('pk').values('pk','username','password','email','role','is_staff','is_superuser','is_active'))
print(json.dumps({'rows':rows,'highest':[u.pk for u in User.objects.all() if is_main(u)],'mail':settings.ACCOUNT_RECOVERY_DELIVERY_MODE,'approval':settings.ACCOUNT_APPROVAL_MODE,'invalidOrderIdentityReferences':bad_counts}))'''
current=json.loads(subprocess.check_output(compose+['exec','-T','web','python','-B','-c',code]))
before=json.loads((private/'identity-before.json').read_text());ids={row['pk'] for row in before}
assert before==[row for row in current['rows'] if row['pk'] in ids]
assert sorted(current['highest'])==sorted(json.loads((private/'main-admin-ids-before.json').read_text()))
result={'existingAccountsPreserved':len(before),'passwordEmailLegacyRoleStaffSuperuserAndActiveUnchanged':True,'highestAdministratorIdsPreserved':True,'extraRegistrationsDuringTask':len(current['rows'])-len(before),'mailMode':current['mail'],'approvalMode':current['approval'],'invalidOrderIdentityReferences':current['invalidOrderIdentityReferences']}
baseline=json.loads((private/'containers-before.json').read_text())
for name,old in baseline.items():
    row=json.loads(subprocess.check_output(['docker','inspect',name.lstrip('/')]))[0]
    assert old['Id']==row['Id'] and old['Image']==row['Image'],name
    assert all(old['State'][key]==row['State'][key] for key in ['Pid','StartedAt','Running']),name
    assert sorted(old['Mounts'],key=lambda m:m['Destination'])==sorted(row['Mounts'],key=lambda m:m['Destination']),name
    assert old['NetworkSettings']['Networks']==row['NetworkSettings']['Networks'],name
result['protectedContainersUnchanged']=[name.lstrip('/') for name in baseline]
result['sprintFinalUnchanged']=subprocess.check_output(['git','rev-parse','sprint-final']).decode().strip()=='133b950221bd9cc1effaa51539abf7f88bb095c1'
assert result['sprintFinalUnchanged']
result['httpLoginStatus']={str(port):int(subprocess.check_output(['curl','-s','--max-time','15','-o','/dev/null','-w','%{http_code}',f'http://127.0.0.1:{port}/accounts/login/'])) for port in [8000,8007,8010,8011]}
assert all(value==200 for value in result['httpLoginStatus'].values())
rows=[json.loads(line) for line in subprocess.check_output(compose+['ps','--format','json']).decode().splitlines()]
result['previewServices']=[{'service':row['Service'],'health':row['Health'],'state':row['State']} for row in rows]
assert len(rows)==5 and all(row['Health']=='healthy' for row in rows)
result['referenceInputSha256']=hashlib.sha256(pathlib.Path('DOREMI.png').read_bytes()).hexdigest()
(root/'deployment-and-protection.json').write_text(json.dumps(result,indent=2))
print('Original account identity/state, highest admins, stable branch and protected resources preserved.')
