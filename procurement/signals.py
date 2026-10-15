from django.db.models.signals import post_save,post_delete
from django.dispatch import receiver
from meals.models import DietPlan,DietMenu,Recipe,Menu
from inventory.models import Ingredient,SupplySpecification
from .workflow import invalidate_plans


@receiver(post_save,sender=DietPlan)
@receiver(post_delete,sender=DietPlan)
def plan_changed(sender,instance,**kwargs):
    if not kwargs.get('raw'):
        invalidate_plans([instance.pk])


@receiver(post_save,sender=DietMenu)
@receiver(post_delete,sender=DietMenu)
def menu_link_changed(sender,instance,**kwargs):
    if not kwargs.get('raw'):
        invalidate_plans([instance.diet_plan_id])


@receiver(post_save,sender=Recipe)
@receiver(post_delete,sender=Recipe)
def recipe_changed(sender,instance,**kwargs):
    if not kwargs.get('raw'):
        invalidate_plans(list(DietMenu.objects.filter(menu_id=instance.menu_id).values_list('diet_plan_id',flat=True)))


@receiver(post_save,sender=Ingredient)
@receiver(post_save,sender=SupplySpecification)
@receiver(post_delete,sender=SupplySpecification)
def master_changed(sender,instance,**kwargs):
    if not kwargs.get('raw'):
        invalidate_plans()
