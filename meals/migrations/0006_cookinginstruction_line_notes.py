from django.db import migrations, models


class Migration(migrations.Migration):
    dependencies = [('meals', '0005_cookinginstruction')]
    operations = [migrations.AddField(
        model_name='cookinginstruction', name='line_notes',
        field=models.JSONField(blank=True, default=dict, verbose_name='재료별 비고'),
    )]
