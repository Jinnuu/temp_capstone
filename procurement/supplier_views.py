"""Supplier contact registry linked explicitly to existing supplier accounts."""
import uuid
from django import forms
from django.contrib import messages
from django.contrib.auth import get_user_model
from django.contrib.auth.decorators import login_required, user_passes_test
from django.db import transaction
from django.db.models.deletion import ProtectedError
from django.db.models import Q
from django.shortcuts import get_object_or_404, redirect, render
from django.views.decorators.http import require_GET, require_POST
from .models import Supplier
from .workflow_views import _can_manage
from accounts.supplier_identity import eligible_order_accounts


class SupplierProfileForm(forms.ModelForm):
    class Meta:
        model = Supplier
        fields = ['category', 'name', 'business_items', 'phone_number', 'fax', 'mobile', 'remarks', 'user']

    def __init__(self, *args, **kwargs):
        super().__init__(*args, **kwargs)
        self.fields['name'].max_length = 50
        self.fields['user'].queryset = eligible_order_accounts(get_user_model().objects.filter(role='SUPPLIER')).filter(
            Q(supplier_profile__isnull=True) | Q(supplier_profile=self.instance.pk)
        ).order_by('name')

    def clean_name(self):
        value = self.cleaned_data['name'].strip()
        if len(value) > 50:
            raise forms.ValidationError('연동 업체명은 50자 이내로 입력하세요.')
        return value

    def clean(self):
        data = super().clean()
        if max(len(data.get('mobile') or ''), len(data.get('phone_number') or '')) > 20:
            raise forms.ValidationError('연동 연락처는 20자 이내로 입력하세요.')
        if self.instance.pk and self.instance.user_id and data.get('user') != self.instance.user:
            raise forms.ValidationError('기존 발주 연결을 보존하기 위해 연동 계정은 변경할 수 없습니다.')
        return data


@login_required
@require_GET
def supplier_list(request):
    query = request.GET.get('q', '').strip()
    suppliers = Supplier.objects.select_related('user').all()
    if query:
        suppliers = suppliers.filter(Q(name__icontains=query) | Q(category__icontains=query) |
            Q(business_items__icontains=query) | Q(phone_number__icontains=query) |
            Q(mobile__icontains=query) | Q(remarks__icontains=query))
    return render(request, 'procurement/supplier_list.html', {
        'suppliers': suppliers, 'query': query, 'can_manage': _can_manage(request.user),
        'available_accounts': eligible_order_accounts(get_user_model().objects.filter(role='SUPPLIER', supplier_profile__isnull=True)).order_by('name'),
    })


def _save(request, instance=None):
    form = SupplierProfileForm(request.POST, instance=instance)
    if not form.is_valid():
        return render(request, 'workflow/form.html', {'title': '거래처 입력 오류', 'form': form}, status=400)
    with transaction.atomic():
        supplier = form.save(commit=False)
        if supplier.user_id is None:
            supplier.user = get_user_model()(username='supplier-' + uuid.uuid4().hex,
                name=supplier.name, role='SUPPLIER')
            supplier.user.set_unusable_password()
        supplier.user.name = supplier.name
        supplier.user.phone_number = supplier.mobile or supplier.phone_number or ''
        supplier.user.full_clean(exclude=['password'])
        supplier.user.save()
        supplier.save()
    messages.success(request, '거래처를 저장했습니다. 기존 발주와 재고는 변경하지 않았습니다.')
    return redirect('procurement:supplier_list')


@login_required
@user_passes_test(_can_manage)
@require_POST
def supplier_create(request):
    return _save(request)


@login_required
@user_passes_test(_can_manage)
@require_POST
def supplier_update(request, pk):
    with transaction.atomic():
        return _save(request, get_object_or_404(Supplier.objects.select_for_update(), pk=pk))


@login_required
@user_passes_test(_can_manage)
@require_POST
def supplier_delete(request, pk):
    try:
        with transaction.atomic():
            supplier = get_object_or_404(Supplier.objects.select_for_update(), pk=pk)
            supplier.delete()  # Historical orders and account identity remain intact.
    except ProtectedError:
        messages.error(request, '포털 계정이 연결된 거래처는 삭제할 수 없습니다. 업체 연결을 먼저 확인하세요.')
        return redirect('procurement:supplier_list')
    messages.success(request, '연락처 현황만 삭제했습니다. 발주 연동 계정과 이력은 유지됩니다.')
    return redirect('procurement:supplier_list')
