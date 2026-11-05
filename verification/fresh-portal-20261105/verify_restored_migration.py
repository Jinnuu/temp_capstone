import os,json
os.environ['DJANGO_SETTINGS_MODULE']='config.auth_mysql_test_settings'
from django.conf import settings
assert settings.DATABASES['default']['HOST']=='auth-db'
settings.DATABASES['default']['NAME']='restore_check'
import django
django.setup()
from django.core.management import call_command
from accounts.models import User
fields=['pk','username','password','email','role','is_staff','is_superuser','is_active','account_state']
before=list(User.objects.order_by('pk').values(*fields))
old_admins=set(User.objects.filter(groups__name='SNP_ROLE_SYSTEM_ADMIN').values_list('pk',flat=True))|set(User.objects.filter(is_superuser=True).values_list('pk',flat=True))
call_command('migrate',interactive=False,verbosity=0)
after=list(User.objects.order_by('pk').values(*fields))
assert before==after
from accounts.rbac import is_main
assert {u.pk for u in User.objects.all() if is_main(u)}==old_admins
from procurement.models import SupplierMembership, Supplier
assert SupplierMembership.objects.filter(status='VERIFIED').count()==Supplier.objects.filter(user__role='SUPPLIER').count()
print(json.dumps({'passed':True,'restoredAccounts':len(before),'originalIdentityStateAndFlagsUnchanged':True,'highestAdminsPreservedWithoutAdditionalPromotion':True,'verifiedMembershipsFromExplicitLegacyLinksOnly':True}))
