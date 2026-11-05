from django.db import migrations


ROLES = ('SYSTEM_ADMIN', 'DIETITIAN', 'INVENTORY_MANAGER', 'COOK', 'VIEWER')


def initialize(apps, schema_editor):
    User = apps.get_model('accounts', 'User')
    Group = apps.get_model('auth', 'Group')
    Policy = apps.get_model('accounts', 'AccessPolicy')
    alias = schema_editor.connection.alias
    groups = {name: Group.objects.using(alias).get_or_create(name='SNP_ROLE_' + name)[0] for name in ROLES}
    Policy.objects.using(alias).get_or_create(pk=1, defaults={'mode': 'manual'})
    for user in User.objects.using(alias).all().iterator():
        user.account_state = 'ACTIVE' if user.is_active else 'LEGACY_INACTIVE'
        user.rbac_managed = True
        user.save(using=alias, update_fields=['account_state', 'rbac_managed'])
        if user.is_superuser or user.role == 'ADMIN':
            user.groups.add(groups['SYSTEM_ADMIN'])
        elif user.role == 'NUTRITIONIST':
            user.groups.add(groups['DIETITIAN'])
            if user.is_staff:
                user.groups.add(groups['INVENTORY_MANAGER'])


class Migration(migrations.Migration):
    dependencies = [('accounts', '0002_accesspolicy_user_access_revision_user_account_state_and_more')]
    operations = [migrations.RunPython(initialize, migrations.RunPython.noop)]
