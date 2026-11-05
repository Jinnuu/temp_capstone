from .money import recorded_amount, accepted_amount
import calendar
import uuid
from collections import defaultdict
from datetime import date, timedelta, datetime
from decimal import Decimal

from django.contrib import messages
from django.contrib.auth import get_user_model
from django.contrib.auth.decorators import login_required, user_passes_test
from django.core.exceptions import ValidationError
from django.db import transaction
from django.db.models import Sum, Q
from django.shortcuts import get_object_or_404, redirect, render
from django.utils import timezone

from forecasting.models import AttendancePrediction
from inventory.models import Ingredient, IngredientCategory, InventoryLog, SupplySpecification, StockLot
from meals.models import DietPlan, Menu, Recipe
from accounts.supplier_identity import eligible_order_accounts
from accounts.access_service import protect_supplier_target, supplier_account_change
from .models import ProcurementPlan, GoodsInspection, PurchaseOrder, OrderItem
from .workflow import (build_preview, create_plan, confirm_orders, inspect_item, record_inventory,
                       save_headcount, invalidate_plans, current_stock)
from .workflow_forms import (HeadcountForm, PreviewForm, SpecificationForm, SupplierForm,
                             CategoryForm, InspectionForm, TransactionForm, RecipeDetailForm)


def _errors(form, exc):
    for error in exc.messages:
        form.add_error(None,error)


@login_required
def hub(request):
    headcount=HeadcountForm(request.POST or None)
    if request.method=='POST' and headcount.is_valid():
        data=headcount.cleaned_data
        try:
            save_headcount(data['plan'].pk,data['manual'],data['final'] if data['confirm'] else None)
            messages.success(request,'식수를 저장했습니다. 변경된 발주예정서는 다시 생성하세요.')
            return redirect('procurement:workflow')
        except ValidationError as exc:
            _errors(headcount,exc)
    rows=[]
    plans=DietPlan.objects.all().order_by('-target_date','meal_type')[:90]
    for plan in plans:
        key={'조식':'breakfast','중식':'lunch','석식':'dinner'}.get(plan.meal_type)
        prediction=AttendancePrediction.objects.filter(prediction_date=plan.target_date,meal_type=key).first()
        rows.append({'plan':plan,'prediction':prediction})
    return render(request,'workflow/hub.html',{'form':headcount,'rows':rows,'plans':ProcurementPlan.objects.order_by('-id')[:30]})


@login_required
def preview(request):
    today=timezone.localdate()
    form=PreviewForm(request.POST or request.GET or None,initial={'start_date':today,'end_date':today,'request_key':uuid.uuid4()})
    result=None
    if form.is_bound and form.is_valid():
        data=form.cleaned_data
        try:
            result=build_preview(data['start_date'],data['end_date'],data['days'])
            if request.method=='POST' and request.POST.get('save'):
                plan=create_plan(data['start_date'],data['end_date'],request.user,data['request_key'],data['days'])
                return redirect('procurement:workflow_plan',pk=plan.pk)
        except ValidationError as exc:
            _errors(form,exc)
    return render(request,'workflow/preview.html',{'form':form,'result':result})


@login_required
def plan_detail(request,pk):
    plan=get_object_or_404(ProcurementPlan,pk=pk)
    if request.method=='POST':
        try:
            with transaction.atomic():
                plan=ProcurementPlan.objects.select_for_update().get(pk=pk)
                for index,detail in enumerate(plan.details):
                    detail['notes']=request.POST.get(f'note_{index}',detail.get('notes',''))[:1000]
                plan.save(update_fields=['details'])
                adjustments={str(line.pk):request.POST.get(f'quantity_{line.pk}',line.package_quantity) for line in plan.lines.all()}
                orders=confirm_orders(plan.pk,request.user,adjustments)
            messages.success(request,f'업체별 구매발주서 {len(orders)}건을 생성했습니다.')
            return redirect('procurement:workflow_plan',pk=pk)
        except ValidationError as exc:
            messages.error(request,' / '.join(exc.messages))
    lines=list(plan.lines.select_related('ingredient','supplier').order_by('order_date','supplier__name','ingredient__category','ingredient__name'))
    for line in lines:
        issued=OrderItem.objects.filter(purchase_order__workflow_plan=plan,ingredient_id=line.ingredient_id,target_date=line.order_date).first()
        line.confirmed_quantity=issued.package_quantity if issued else line.package_quantity
    return render(request,'workflow/plan.html',{'plan':plan,'blank_inputs':request.GET.get('blank')=='1','lines':lines})


@login_required
def inspections(request):
    orders=PurchaseOrder.objects.prefetch_related('items__ingredient','items__inspection').select_related('supplier').order_by('supplier__name','id')
    target=request.GET.get('date','')
    if target:
        try:
            selected_date=date.fromisoformat(target)
            orders=orders.filter(items__target_date=selected_date).distinct()
        except ValueError:
            messages.error(request,'검수 대상 날짜가 올바르지 않습니다.')
            orders=orders.none()
    supplier=request.GET.get('supplier','')
    if supplier:
        orders=orders.filter(supplier_id=int(supplier)) if supplier.isdigit() else orders.none()
    return render(request,'workflow/inspections.html',{'orders':orders,'target_date':target,'suppliers':get_user_model().objects.filter(purchase_orders__isnull=False).distinct().order_by('name')})


@login_required
def inspection(request,pk):
    item=get_object_or_404(OrderItem.objects.select_related('ingredient','purchase_order__supplier'),pk=pk)
    existing=GoodsInspection.objects.filter(order_item=item).first()
    initial={'delivered':item.required_qty,'accepted':item.required_qty,'specification':item.spec_snapshot or item.ingredient.spec or ''}
    if existing:
        initial.update(delivered=existing.delivered_qty,accepted=existing.accepted_qty,specification=existing.specification,notes=existing.notes,condition=existing.condition,expiration=existing.expiration_date)
    form=InspectionForm(request.POST or None,initial=initial)
    if request.method=='POST' and form.is_valid():
        try:
            inspect_item(item.pk,request.user,**form.cleaned_data)
            messages.success(request,'합격 수량만 입고 반영했습니다.')
            return redirect('procurement:workflow_inspections')
        except ValidationError as exc:
            _errors(form,exc)
    return render(request,'workflow/form.html',{'title':f'급식물품 검수 기록 · {item.ingredient.name} ({item.ingredient.unit})','form':form,'inspection':existing,'supplier_fulfillment':getattr(item.purchase_order,'fulfillment',None),'supplier_delivery':getattr(item,'delivery_plan',None),'supplier_base_unit':item.ingredient.unit})


@login_required
def stock_transaction(request):
    form=TransactionForm(request.POST or None,initial={'request_key':uuid.uuid4()})
    if request.method=='POST' and form.is_valid():
        data=dict(form.cleaned_data);data['ingredient_id']=data.pop('ingredient').pk
        try:
            record_inventory(actor=request.user,**data)
            messages.success(request,'재고 거래를 저장했습니다.')
            return redirect('procurement:workflow_ledger')
        except ValidationError as exc:
            _errors(form,exc)
    return render(request,'workflow/form.html',{'title':'선입고·사용·재고 조정 (기준 단위)','form':form})


def _can_manage(user):
    from accounts.rbac import can
    return can(user, 'catalog.write')


@login_required
@user_passes_test(_can_manage)
def specifications(request,pk=None):
    instance=get_object_or_404(SupplySpecification,pk=pk) if pk else None
    form=SpecificationForm(request.POST or None,instance=instance)
    if request.method=='POST' and form.is_valid():
        with transaction.atomic():
            spec=form.save()
            Ingredient.objects.filter(pk=spec.ingredient_id).update(supplier=spec.supplier)
            invalidate_plans()
        messages.success(request,'납품규격을 저장했습니다. 기존 발주예정서를 재계산하세요.')
        return redirect('procurement:workflow_specs')
    return render(request,'workflow/master.html',{'title':'업체·납품규격 관리','form':form,'specs':SupplySpecification.objects.select_related('ingredient','supplier').order_by('supplier__name','ingredient__name')})


@login_required
@user_passes_test(_can_manage)
def suppliers(request,pk=None):
    from accounts.supplier_identity import eligible_order_accounts
    user=get_object_or_404(eligible_order_accounts().filter(role='SUPPLIER'),pk=pk) if pk else None
    if user and request.method != 'POST':
        protect_supplier_target(request.user, user)
    initial={name:getattr(user,name) for name in ['username','name','phone_number']} if user else {}
    form=SupplierForm(request.POST or None,initial=initial)
    if request.method=='POST' and form.is_valid():
        data=form.cleaned_data
        if get_user_model().objects.filter(username=data['username']).exclude(pk=user.pk if user else None).exists():
            form.add_error('username','중복된 업체 식별자입니다.')
        else:
            with supplier_account_change(request.user, user.pk if user else None) as locked:
                user=locked or get_user_model()(role='SUPPLIER')
                for key,value in data.items():setattr(user,key,value)
                if not user.pk:user.set_unusable_password()
                user.save()
            return redirect('procurement:workflow_suppliers')
    return render(request,'workflow/master.html',{'title':'업체 관리','form':form,'suppliers':eligible_order_accounts().filter(role='SUPPLIER').order_by('name')})


@login_required
@user_passes_test(_can_manage)
def categories(request):
    form=CategoryForm(request.POST or None)
    if request.method=='POST' and form.is_valid():
        data=form.cleaned_data
        with transaction.atomic():
            category,created=IngredientCategory.objects.get_or_create(name=data['name'])
            if not created and not data['ingredients'] and not data['rename_from']:
                form.add_error('name','이미 존재하는 분류입니다.')
            else:
                if data['rename_from']:
                    Ingredient.objects.filter(category=data['rename_from']).update(category=category.name)
                    IngredientCategory.objects.filter(name=data['rename_from']).exclude(pk=category.pk).delete()
                data['ingredients'].update(category=category.name)
                invalidate_plans()
                messages.success(request,'카테고리와 품목 분류를 저장했습니다.')
                return redirect('procurement:workflow_categories')
    names=sorted(set(IngredientCategory.objects.values_list('name',flat=True))|set(Ingredient.objects.exclude(category__isnull=True).exclude(category='').values_list('category',flat=True)))
    return render(request,'workflow/master.html',{'title':'식자재 카테고리·오분류 정정','form':form,'categories':names})


@login_required
def recipe_detail(request,pk=None):
    recipe=get_object_or_404(Recipe,pk=pk) if pk else None
    form=RecipeDetailForm(request.POST or None,instance=recipe)
    if request.method=='POST' and form.is_valid():
        from meals.change_policy import guard_menu_change, mark_menu_change
        try:
            with transaction.atomic():
                affected = {form.cleaned_data['menu'].pk}
                if recipe:
                    affected.add(recipe.menu_id)
                guard_menu_change(affected)
                saved=form.save()
                notes=request.POST.get('cooking_notes','')
                Menu.objects.filter(pk=saved.menu_id).update(cooking_notes=notes)
                mark_menu_change(affected)
            return redirect('procurement:workflow_recipes')
        except ValidationError as exc:
            _errors(form, exc)
    return render(request,'workflow/recipes.html',{'title':'레시피 단위·조리 정보','form':form,'recipe':recipe,'recipes':Recipe.objects.select_related('menu','ingredient').order_by('menu__name','ingredient__name')})


@login_required
def ledger(request):
    try:
        start=date.fromisoformat(request.GET.get('start_date',str(timezone.localdate()-timedelta(days=timezone.localdate().weekday()))))
        end=date.fromisoformat(request.GET.get('end_date',str(start+timedelta(days=6))))
        if end<start or (end-start).days>366:raise ValueError()
    except ValueError:
        messages.error(request,'올바른 조회 기간을 입력하세요.');start=timezone.localdate();end=start+timedelta(days=6)
    rows=[]
    for ing in Ingredient.objects.select_related('supplier').order_by('category','name'):
        def total(qs):
            result=defaultdict(lambda:Decimal('0'))
            for row in qs.values('log_type').annotate(qty=Sum('quantity')):result[row['log_type']]=row['qty']
            return result
        opening=total(InventoryLog.objects.filter(ingredient=ing,transaction_date__date__lt=start))
        inside=total(InventoryLog.objects.filter(ingredient=ing,transaction_date__date__range=(start,end)))
        initial=opening['입고']-opening['출고']-opening['폐기']+opening['조정']
        closing=initial+inside['입고']-inside['출고']-inside['폐기']+inside['조정']
        rows.append({'ingredient':ing,'opening':initial,'incoming':inside['입고'],'outgoing':inside['출고'],'waste':inside['폐기'],'adjustment':inside['조정'],'closing':closing,'warning':closing<0})
    return render(request,'workflow/ledger.html',{'rows':rows,'start':start,'end':end,'lots':StockLot.objects.select_related('incoming_log__ingredient').filter(remaining_quantity__gt=0).order_by('incoming_log__transaction_date')})


@login_required
def settlement(request):
    try:
        month=request.GET.get('month',timezone.localdate().strftime('%Y-%m'))
        start=datetime.strptime(month,'%Y-%m').date();end=date(start.year,start.month,calendar.monthrange(start.year,start.month)[1])
    except ValueError:
        messages.error(request,'올바른 연월을 선택하세요.');start=timezone.localdate().replace(day=1);end=date(start.year,start.month,calendar.monthrange(start.year,start.month)[1])
    rows=[]
    suppliers=get_user_model().objects.filter(Q(purchase_orders__items__target_date__range=(start,end))|Q(purchase_orders__items__inspection__inspected_at__date__range=(start,end))).distinct().order_by('name')
    selected=request.GET.get('supplier')
    if selected and selected.isdigit():suppliers=suppliers.filter(pk=int(selected))
    for supplier in suppliers:
        items=OrderItem.objects.filter(purchase_order__supplier=supplier,target_date__range=(start,end))
        inspections=GoodsInspection.objects.filter(order_item__purchase_order__supplier=supplier,inspected_at__date__range=(start,end)).select_related('order_item')
        ordered=sum((recorded_amount(item) for item in items), Decimal('0'))
        inspected_value=sum((accepted_amount(x.order_item, x.accepted_qty) for x in inspections if x.order_item.required_qty),Decimal('0'))
        rows.append({'supplier':supplier,'ordered_amount':ordered,'inspected_amount':inspected_value,'uninspected':items.filter(inspection__isnull=True).count()})
    return render(request,'workflow/settlement.html',{'rows':rows,'start':start,'end':end,'suppliers':eligible_order_accounts().filter(role='SUPPLIER').order_by('name')})
