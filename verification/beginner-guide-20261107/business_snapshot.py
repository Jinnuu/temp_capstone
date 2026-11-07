import django,json,hashlib
django.setup()
from django.conf import settings
assert settings.DATABASES['default']['HOST']=='auth-db'
assert settings.DATABASES['default']['NAME']=='snp_auth_verification'
from django.apps import apps
result={}
for model in apps.get_models():
    if model._meta.app_label in ('meals','procurement','inventory','forecasting'):
        rows=list(model.objects.order_by('pk').values())
        result[model._meta.label]={'count':len(rows),'sha256':hashlib.sha256(json.dumps(rows,default=str,sort_keys=True).encode()).hexdigest()}
print(json.dumps(result,indent=2))
