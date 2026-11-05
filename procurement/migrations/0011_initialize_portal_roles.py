from django.db import migrations


def initialize(apps, schema_editor):
    alias=schema_editor.connection.alias
    User=apps.get_model('accounts','User');Group=apps.get_model('auth','Group')
    Supplier=apps.get_model('procurement','Supplier');Membership=apps.get_model('procurement','SupplierMembership')
    main,_=Group.objects.using(alias).get_or_create(name='SNP_ROLE_MAIN_ADMIN')
    Group.objects.using(alias).get_or_create(name='SNP_ROLE_SUB_ADMIN')
    supplier_group,_=Group.objects.using(alias).get_or_create(name='SNP_ROLE_SUPPLIER')
    for user in User.objects.using(alias).all().iterator():
        old_groups=user.groups.using(alias).filter(name='SNP_ROLE_SYSTEM_ADMIN')
        if user.is_superuser or old_groups.exists() or (not user.rbac_managed and user.role=='ADMIN'):
            user.groups.add(main)
            user.groups.remove(*list(old_groups))
        if user.role=='SUPPLIER':
            user.groups.add(supplier_group)
            # Only an existing explicit admin-created OneToOne is trusted.
            profile=Supplier.objects.using(alias).filter(user=user).first()
            Membership.objects.using(alias).get_or_create(account=user,defaults={
                'supplier':profile,'status':'VERIFIED' if profile else 'PENDING',
                'requested_company':profile.name if profile else (user.name or user.username),
                'contact_name':'','contact_phone':user.phone_number or '',
                'review_note':'기존 명시적 거래처 계정 연결 보존' if profile else '기존 계정의 업체 소속 확인 필요',
            })


class Migration(migrations.Migration):
    dependencies=[('accounts','0004_adminrolerequest_announcement'),('procurement','0010_supplierdeliveryline_supplierfulfillment_and_more')]
    operations=[migrations.RunPython(initialize,migrations.RunPython.noop)]
