"""Schema/count metadata only; run inside the existing Preview web container.
No account attributes, settings, credentials, hashes, tokens or data rows printed.
"""
import os,json,django
os.environ.setdefault('DJANGO_SETTINGS_MODULE','config.settings')
django.setup()
from django.db import connection,transaction
with connection.cursor() as cursor:
    cursor.execute('SET TRANSACTION READ ONLY')
with transaction.atomic():
    tables=connection.introspection.table_names()
    result={'new_delivery_tables_present':any(t.startswith('procurement_delivery') for t in tables),'counts':{},'columns':{}}
    with connection.cursor() as cursor:
        for table in ['accounts_user','procurement_purchaseorder','procurement_orderitem','procurement_goodsinspection','inventory_inventorylog']:
            cursor.execute('SELECT COUNT(*) FROM '+connection.ops.quote_name(table))
            result['counts'][table]=cursor.fetchone()[0]
        result['columns']['procurement_goodsinspection']=[x.name for x in connection.introspection.get_table_description(cursor,'procurement_goodsinspection')]
print(json.dumps(result,indent=2))
