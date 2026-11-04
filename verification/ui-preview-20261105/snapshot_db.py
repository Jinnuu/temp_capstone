"""Read-only digest of synthetic preview business tables; never prints rows."""
import os,json,hashlib
os.environ.setdefault('DJANGO_SETTINGS_MODULE','config.preview_settings')
import django
django.setup()
from django.conf import settings
from django.db import connection
assert settings.DATABASES['default']['NAME']=='snp_ui_preview'
assert settings.DATABASES['default']['HOST']=='db'
result={}
with connection.cursor() as cursor:
    for table in connection.introspection.table_names(cursor):
        if not table.startswith(('accounts_','meals_','forecasting_','inventory_','procurement_')):
            continue
        cursor.execute('SELECT * FROM '+connection.ops.quote_name(table))
        rows=sorted(json.dumps(row,default=str,ensure_ascii=False) for row in cursor.fetchall())
        result[table]={'rows':len(rows),'sha256':hashlib.sha256('\n'.join(rows).encode()).hexdigest()}
print(json.dumps(result,indent=2))
