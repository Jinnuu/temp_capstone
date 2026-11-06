"""Read-only whole-schema fingerprints. Never output field values or credentials."""
import os, json, hashlib
import django
django.setup()
from django.conf import settings
from django.db import connection
from django.core.serializers.json import DjangoJSONEncoder
from accounts.models import User
from accounts.rbac import is_main

name=settings.DATABASES['default']['NAME'];host=settings.DATABASES['default']['HOST']
assert (name=='snp_ui_preview' and host=='db' and getattr(settings,'SNP_UI_PREVIEW',False)) or (name=='restore_check' and host=='auth-db')
normalize_pk=int(os.environ.get('SNP_NORMALIZE_ADMIN_PK','0'))
audit_max=int(os.environ['SNP_AUDIT_BASE_MAX']) if 'SNP_AUDIT_BASE_MAX' in os.environ else None
result={}
with connection.cursor() as cursor:
    for table in sorted(connection.introspection.table_names()):
        quoted=connection.ops.quote_name(table)
        cursor.execute('SELECT * FROM '+quoted)
        columns=[c[0] for c in cursor.description]
        rows=[]
        for record in cursor.fetchall():
            item=dict(zip(columns,record))
            if table=='accounts_user' and item['id']==normalize_pk and item['username']=='admin':item['username']='verify-admin'
            if table=='accounts_accessaudit' and audit_max is not None and item['id']>audit_max:continue
            rows.append(json.dumps(item,cls=DjangoJSONEncoder,sort_keys=True,ensure_ascii=False,separators=(',',':')))
        digest=hashlib.sha256(('\n'.join(sorted(rows))).encode()).hexdigest()
        result[table]={'rows':len(rows),'fingerprint':digest}
    cursor.execute('SELECT COALESCE(MAX(id),0), COUNT(*) FROM accounts_accessaudit');maximum,audits=cursor.fetchone()
users=User.objects.only('pk','username','is_active','is_staff','is_superuser','account_state','rbac_managed','role').prefetch_related('groups')
admins=[{'pk':u.pk,'username':u.username,'active':u.is_active,'staff':u.is_staff,'superuser':u.is_superuser,'state':u.account_state} for u in users if is_main(u)]
print(json.dumps({'tables':result,'accounts':User.objects.count(),'main':admins,'admin_collision':User.objects.filter(username='admin').exists(),'verify_admin_count':User.objects.filter(username='verify-admin').count(),'audit_max':maximum,'audit_count':audits},indent=2))
