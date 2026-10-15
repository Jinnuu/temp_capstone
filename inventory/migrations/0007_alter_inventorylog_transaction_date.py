from django.db import migrations, models
import django.utils.timezone


class Migration(migrations.Migration):
    dependencies = [('inventory', '0006_ingredient_description')]
    operations = [
        migrations.AlterField(
            model_name='inventorylog', name='transaction_date',
            field=models.DateTimeField(default=django.utils.timezone.now),
        ),
    ]
