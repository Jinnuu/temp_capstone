"""Fixed application roles built on Django Groups; legacy identities stay intact."""
from django.conf import settings

PREFIX='SNP_ROLE_'
ROLE_LABELS={'SYSTEM_ADMIN':'시스템 관리자','DIETITIAN':'영양사','INVENTORY_MANAGER':'식자재·재고 담당자','COOK':'조리사','VIEWER':'조회 전용'}
BUSINESS={'dashboard.read','meals.read','meals.write','forecast.read','forecast.write','procurement.read','procurement.write','inspection.read','inspection.write','inventory.read','inventory.write','cooking.read','cooking.write','reports.read'}
ROLE_CAPS={
 'SYSTEM_ADMIN': BUSINESS|{'accounts.manage','catalog.read','catalog.write'},
 'DIETITIAN':BUSINESS|{'catalog.read'},
 'INVENTORY_MANAGER':{'dashboard.read','meals.read','forecast.read','procurement.read','procurement.write','inspection.read','inspection.write','inventory.read','inventory.write','cooking.read','reports.read','catalog.read','catalog.write'},
 'COOK':{'dashboard.read','meals.read','cooking.read','cooking.write'},
 'VIEWER':{x for x in BUSINESS if x.endswith('.read')}|{'catalog.read'},
}


def approval_mode():
    mode=getattr(settings,'ACCOUNT_APPROVAL_MODE','manual')
    if mode not in ('auto','manual'):
        raise ValueError('ACCOUNT_APPROVAL_MODE must be auto or manual')
    return mode


def account_can_login(user):
    return bool(user and user.is_active and (not user.rbac_managed or user.account_state=='ACTIVE'))


def roles(user):
    if not getattr(user,'is_authenticated',False):return set()
    if user.is_superuser:return {'SYSTEM_ADMIN'}
    if user.rbac_managed:
        return {n[len(PREFIX):] for n in user.groups.values_list('name',flat=True) if n.startswith(PREFIX) and n[len(PREFIX):] in ROLE_CAPS}
    # Compatibility for direct legacy user creation; migrated/public accounts are managed.
    if user.is_staff or user.role=='ADMIN':return {'SYSTEM_ADMIN'}
    if user.role=='NUTRITIONIST':return {'DIETITIAN'}
    return set()


def capabilities(user):
    if not getattr(user,'is_authenticated',False) or not account_can_login(user):return set()
    if user.role=='SUPPLIER' and not user.is_staff and not user.is_superuser:return set()
    return set().union(*(ROLE_CAPS[r] for r in roles(user)))


def can(user,cap):return cap in capabilities(user)

# Endpoint-specific exceptions keep headcount confirmation separate from purchasing.
SPECIAL={
 'procurement:workflow':('procurement.read','forecast.write'),
 'procurement:workflow_inspections':('inspection.read','inspection.write'),
 'procurement:workflow_inspection':('inspection.read','inspection.write'),
 'procurement:workflow_transaction':('inventory.read','inventory.write'),
 'procurement:workflow_ledger':('inventory.read','inventory.write'),
 'procurement:workflow_settlement':('reports.read','procurement.write'),
 'procurement:workflow_recipes':('meals.read','meals.write'),
 'procurement:workflow_recipe_edit':('meals.write','meals.write'),
 'procurement:workflow_specs':('catalog.write','catalog.write'),
 'procurement:workflow_spec_edit':('catalog.write','catalog.write'),
 'procurement:workflow_categories':('catalog.write','catalog.write'),
 'procurement:workflow_suppliers':('accounts.manage','accounts.manage'),
 'procurement:workflow_supplier_edit':('accounts.manage','accounts.manage'),
 'procurement:supplier_create':('catalog.write','catalog.write'),
 'procurement:supplier_update':('catalog.write','catalog.write'),
 'procurement:supplier_delete':('catalog.write','catalog.write'),
 'procurement:doc_cooking_instruction':('cooking.read','cooking.write'),
 'meals:deduct_inventory':('inventory.write','inventory.write'),
}
EDIT_NAMES={'mealplan_create','monthly_mealplan_create','weekly_mealplan_create','mealplan_bulk_upload','recipe_upload_page','recipe_upload_api','menu_create','menu_update','menu_delete','recipe_create','ingredient_create','ingredient_update','ingredient_upload','ingredient_upload_legacy','inventory_log_create','ingredient_stock_adjust','order_create','order_from_mealplan','order_status_update','supplier_create','supplier_update','supplier_delete','prediction_create','forecasting_home'}


def required_capability(name,method='GET'):
    safe=method in ('GET','HEAD','OPTIONS')
    if name.startswith('account_admin_'):return 'accounts.manage'
    if name in ('home','ui_compare'):return 'dashboard.read'
    if name=='docs_index':return 'reports.read'
    if name.startswith('admin:'):return 'accounts.manage'
    if name in SPECIAL:return SPECIAL[name][0 if safe else 1]
    if ':' not in name:return None
    namespace,view=name.split(':',1)
    if namespace=='meals':domain='cooking' if view.startswith('cooking_') else 'meals'
    elif namespace=='inventory':domain='inventory'
    elif namespace=='forecasting':domain='forecast'
    elif namespace=='procurement':domain='procurement'
    else:return None
    if ('report' in view or view.startswith(('doc_','export_')) or 'document' in view) and safe:return 'cooking.read' if 'cooking' in view else domain+'.read'
    return domain+'.'+('write' if not safe or view in EDIT_NAMES else 'read')
