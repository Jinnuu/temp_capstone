"""Exercise deployed seed with writes blocked before SQL execution."""
import django
django.setup()
from django.conf import settings
from django.db import connection
from accounts.models import User
import runpy,io,contextlib,json
assert settings.DATABASES['default']['NAME']=='snp_ui_preview' and settings.DATABASES['default']['HOST']=='db'
before=User.objects.count()
assert User.objects.filter(pk=1,username='admin',is_active=True).exists()
verbs={}
def readonly(execute,sql,params,many,context):
    verb=sql.lstrip().split(None,1)[0].upper()
    if verb not in {'SELECT','SHOW','SET','SAVEPOINT','RELEASE','BEGIN','COMMIT','ROLLBACK'}:
        raise RuntimeError('Seed attempted a write; blocked before execution')
    verbs[verb]=verbs.get(verb,0)+1
    return execute(sql,params,many,context)
with connection.execute_wrapper(readonly),contextlib.redirect_stdout(io.StringIO()):
    runpy.run_path('seed_preview.py',run_name='__main__')
assert before==User.objects.count() and not User.objects.filter(username='verify-admin').exists()
print(json.dumps({'passed':True,'write_statements_executed':0,'accounts_before':before,'accounts_after':User.objects.count(),'verify_admin_recreated':False,'readonly_sql_statement_counts':verbs}))
