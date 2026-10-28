# Generated for Supplier model

from django.conf import settings
from django.db import migrations, models
import django.db.models.deletion


class Migration(migrations.Migration):

    dependencies = [
        migrations.swappable_dependency(settings.AUTH_USER_MODEL),
        ('procurement', '0004_remove_orderitem_unique_order_ingredient_date_and_more'),
    ]

    operations = [
        migrations.CreateModel(
            name='Supplier',
            fields=[
                ('id', models.BigAutoField(auto_created=True, primary_key=True, serialize=False, verbose_name='ID')),
                ('category', models.CharField(help_text='예: 부식업체, 농산물, 육류 등', max_length=50, verbose_name='구분')),
                ('name', models.CharField(max_length=100, verbose_name='상호명')),
                ('business_items', models.CharField(blank=True, help_text='예: 곡류, 농산물 등', max_length=200, null=True, verbose_name='거래품목')),
                ('phone_number', models.CharField(blank=True, max_length=30, null=True, verbose_name='전화번호')),
                ('fax', models.CharField(blank=True, max_length=30, null=True, verbose_name='팩스')),
                ('mobile', models.CharField(blank=True, max_length=30, null=True, verbose_name='핸드폰')),
                ('remarks', models.TextField(blank=True, null=True, verbose_name='비고(이메일)')),
                ('created_at', models.DateTimeField(auto_now_add=True, verbose_name='등록일')),
                ('updated_at', models.DateTimeField(auto_now=True, verbose_name='수정일')),
                ('user', models.OneToOneField(blank=True, null=True, on_delete=django.db.models.deletion.SET_NULL, related_name='supplier_profile', to=settings.AUTH_USER_MODEL, verbose_name='연동 계정')),
            ],
            options={
                'verbose_name': '거래처(공급업체)',
                'verbose_name_plural': '거래처(공급업체) 목록',
                'ordering': ['name'],
            },
        ),
    ]
