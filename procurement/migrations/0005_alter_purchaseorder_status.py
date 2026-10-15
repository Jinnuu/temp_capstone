from django.db import migrations, models


class Migration(migrations.Migration):
    dependencies = [('procurement', '0004_remove_orderitem_unique_order_ingredient_date_and_more')]
    operations = [
        migrations.AlterField(
            model_name='purchaseorder', name='status',
            field=models.CharField(choices=[('대기', '대기'), ('승인', '승인'), ('완료', '완료')], default='대기', max_length=10),
        ),
    ]
