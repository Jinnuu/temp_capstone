"""Supplier actions never write inspection, ledger, stock, prices or order lines."""
from datetime import date
from decimal import Decimal, InvalidOperation
from django.db import transaction
from django.utils import timezone
from django.core.exceptions import PermissionDenied
from accounts.models import User
from accounts.rbac import can
from accounts.access_service import audit, policy_lock, AccessRejected
from .models import Supplier, SupplierMembership, SupplierFulfillment, SupplierDeliveryLine, PurchaseOrder

TRANSITIONS = {
    'NEW': {'ACKNOWLEDGED','ACCEPTED','REJECTED'},
    'ACKNOWLEDGED': {'ACCEPTED','REJECTED'},
    'ACCEPTED': {'PREPARING'},
    'PREPARING': {'DISPATCHED'},
    'DISPATCHED': set(), 'REJECTED': set(),
}


def verified_membership(user, lock=False):
    if not user.is_active or not can(user,'portal.read') or user.role!='SUPPLIER':
        raise PermissionDenied('공급업체 전용 기능입니다.')
    query = SupplierMembership.objects.select_related('supplier')
    if lock:
        query = query.select_for_update()
    membership = query.filter(account=user, status='VERIFIED', supplier__user__isnull=False).first()
    if not membership:
        raise PermissionDenied('업체 소속 확인이 완료된 후 이용할 수 있습니다.')
    if membership.supplier.user.role != 'SUPPLIER':
        raise PermissionDenied('거래처 연동 계정을 확인해야 합니다.')
    return membership


@transaction.atomic
def review_membership(actor, pk, supplier_id, revision, *, create_company=False, reject=False, note=''):
    policy_lock()
    actor = User.objects.select_for_update().get(pk=actor.pk)
    member = SupplierMembership.objects.select_for_update().select_related('account').get(pk=pk)
    if not can(actor,'suppliers.verify') or actor.pk==member.account_id:
        raise AccessRejected('자신의 업체 연결은 승인할 수 없으며 관리자 권한이 필요합니다.')
    from accounts.rbac import is_main,is_admin_identity
    if not is_main(actor) and is_admin_identity(member.account):
        raise AccessRejected('최고관리자만 관리자 계정의 업체 연결을 변경할 수 있습니다.')
    if revision != member.revision or len(note)>500:
        raise AccessRejected('다른 관리자가 변경했습니다. 입력값을 확인하고 새로고침하세요.', code='conflict')
    before={'status':member.status,'supplier':member.supplier_id}
    if reject:
        if member.status=='VERIFIED':
            raise AccessRejected('확인 완료 연결은 거절로 바꾸지 않고 새 연결을 검증해야 합니다.')
        if not note.strip():raise AccessRejected('거절 사유가 필요합니다.')
        member.status='REJECTED'
    else:
        if not note.strip():raise AccessRejected('업체 소속을 확인한 근거를 기록하세요.')
        if create_company:
            if supplier_id:raise AccessRejected('기존 업체 연결과 신규 생성을 동시에 선택할 수 없습니다.')
            name=' '.join(member.requested_company.split())
            if Supplier.objects.filter(name__iexact=name).exists():
                raise AccessRejected('동일 상호가 있습니다. 확인 후 기존 업체를 선택하세요.')
            if Supplier.objects.filter(user=member.account).exists():
                raise AccessRejected('이미 연동된 업체가 있습니다. 기존 업체를 선택하세요.')
            supplier=Supplier.objects.create(name=name,category='미분류',phone_number=member.contact_phone,user=member.account)
        else:
            try:supplier=Supplier.objects.select_for_update().get(pk=supplier_id)
            except (Supplier.DoesNotExist,ValueError,TypeError):raise AccessRejected('연결할 거래처를 선택하세요.')
        if Supplier.objects.filter(user=member.account).exclude(pk=supplier.pk).exists():
            raise AccessRejected('기존 발주용 업체 계정의 소속은 변경하지 않습니다. 새 직원 계정으로 신청하세요.')
        if supplier.user_id is None or supplier.user.role!='SUPPLIER':
            raise AccessRejected('기존 발주용 공급업체 계정이 연결된 거래처만 승인할 수 있습니다.')
        member.supplier=supplier
        member.status='VERIFIED'
    member.verified_by=actor;member.reviewed_at=timezone.now();member.review_note=note.strip();member.revision+=1
    member.save()
    audit(actor,member.account,'supplier.membership_reviewed',before,{'status':member.status,'supplier':member.supplier_id})
    return member


def update_fulfillment(actor, order_id, *, state, revision, delivery_date=None, quantities=None, rejection_reason='', notes=''):
    try:
        with transaction.atomic():
            # Same mutex order as role changes/membership changes prevents stale ownership.
            policy_lock()
            actor=User.objects.select_for_update().get(pk=actor.pk)
            member=verified_membership(actor,lock=True)
            order=PurchaseOrder.objects.select_for_update().get(pk=order_id,supplier_id=member.supplier.user_id)
            row=SupplierFulfillment.objects.select_for_update().filter(order=order).first()
            current=row.state if row else 'NEW';current_revision=row.revision if row else 0
            if revision!=current_revision:raise AccessRejected('다른 요청이 먼저 저장됐습니다. 새로고침하세요.',code='conflict')
            if order.status in ('완료','배송완료') or order.items.filter(inspection__isnull=False).exists():
                raise AccessRejected('검수가 시작된 발주는 공급업체가 수정할 수 없습니다.')
            if order.needs_review or order.status not in ('대기','승인'):
                raise AccessRejected('변경 검토 또는 취소된 발주는 처리할 수 없습니다.')
            if current in ('DISPATCHED','REJECTED') or (state!=current and state not in TRANSITIONS[current]):
                raise AccessRejected('허용되지 않은 수주 상태 전이입니다.')
            if len(rejection_reason)>500 or len(notes)>1000:raise AccessRejected('입력 길이를 확인하세요.')
            if state=='REJECTED' and not rejection_reason.strip():raise AccessRejected('거절 사유가 필요합니다.')
            items=list(order.items.select_related('ingredient').all())
            if not items:raise AccessRejected('품목이 없는 발주는 처리할 수 없습니다.')
            supplied=quantities or {}
            if not isinstance(supplied,dict) or set(supplied)-{str(item.pk) for item in items}:raise AccessRejected('다른 발주 품목은 수정할 수 없습니다.')
            planned={}
            scheduling=state in ('ACCEPTED','PREPARING','DISPATCHED')
            if scheduling:
                try:when=date.fromisoformat(str(delivery_date))
                except (ValueError,TypeError):raise AccessRejected('납품 예정일을 입력하세요.')
                if when<timezone.localdate():raise AccessRejected('납품 예정일은 오늘 이후여야 합니다.')
                for item in items:
                    try:
                        raw=supplied.get(str(item.pk),item.required_qty)
                        value=Decimal(str(raw))
                        if not value.is_finite() or value<0 or value>item.required_qty or value.as_tuple().exponent < -6:raise ValueError()
                    except (ValueError,InvalidOperation,TypeError):raise AccessRejected('예정량은 발주 기준량 이하의 유효한 수량이어야 합니다.')
                    planned[item.pk]=value
                if not any(planned.values()):raise AccessRejected('납품할 수량이 필요합니다.')
            else:
                when=None
                if supplied:raise AccessRejected('수락 이후에 납품 예정량을 입력하세요.')
            row=row or SupplierFulfillment(order=order)
            row.state=state;row.delivery_date=when;row.rejection_reason=rejection_reason.strip() if state=='REJECTED' else ''
            row.notes=notes.strip();row.updated_by=actor;row.revision=current_revision+1;row.save()
            for item_id,value in planned.items():SupplierDeliveryLine.objects.update_or_create(order_item_id=item_id,defaults={'planned_quantity':value})
            audit(actor,actor,'supplier.fulfillment_changed',{'order':order.pk,'state':current,'revision':current_revision},{'order':order.pk,'state':state,'revision':row.revision})
            return row
    except PurchaseOrder.DoesNotExist:
        # The caller maps this to the same 404 as an absent order; no owner disclosure.
        raise
