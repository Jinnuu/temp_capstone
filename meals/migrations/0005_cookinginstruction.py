from django.db import migrations, models
import django.db.models.deletion


class Migration(migrations.Migration):
    dependencies = [('meals', '0004_dietplan_final_headcount_and_more')]
    operations = [migrations.CreateModel(
        name='CookingInstruction',
        fields=[
            ('id', models.BigAutoField(auto_created=True, primary_key=True, serialize=False, verbose_name='ID')),
            ('instructions', models.TextField(blank=True, default='', verbose_name='현장 조리 지시·비고')),
            ('inventory_instructions', models.TextField(blank=True, default='', verbose_name='재고 사용 지시')),
            ('revision', models.PositiveIntegerField(default=0)),
            ('updated_at', models.DateTimeField(auto_now=True)),
            ('diet_plan', models.OneToOneField(on_delete=django.db.models.deletion.CASCADE, related_name='cooking_instruction', to='meals.dietplan')),
        ],
    )]
