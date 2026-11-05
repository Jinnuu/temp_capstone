"""Explicit MAIN_ADMIN decisions; a request never changes login or permissions."""
from django.db import transaction
from django.utils import timezone
from .models import User, AdminRoleRequest
from .rbac import roles, is_main, is_admin_identity
from .access_service import policy_lock, audit, AccessRejected, change_access


@transaction.atomic
def submit_request(actor, reason):
    policy_lock()
    actor = User.objects.select_for_update().get(pk=actor.pk)
    if not actor.is_active or is_admin_identity(actor):
        raise AccessRejected('일반 활성 계정만 관리자 권한을 신청할 수 있습니다.')
    reason = reason.strip()
    if not reason or len(reason) > 1000:
        raise AccessRejected('신청 사유를 1~1000자로 입력하세요.')
    row, created = AdminRoleRequest.objects.get_or_create(user=actor, defaults={'reason': reason})
    if not created and row.status == 'PENDING':
        return row
    before = {'status': row.status} if not created else {}
    row.reason = reason
    row.status = 'PENDING'
    row.reviewed_by = None
    row.reviewed_at = None
    row.decision_note = ''
    row.revision += not created
    row.save()
    audit(actor, actor, 'admin.request_submitted', before, {'status': row.status})
    return row


def review_request(actor, pk, decision, revision, note=''):
    target = None
    try:
        with transaction.atomic():
            policy_lock()
            actor = User.objects.select_for_update().get(pk=actor.pk)
            row = AdminRoleRequest.objects.select_for_update().select_related('user').get(pk=pk)
            target = row.user
            if not is_main(actor):
                raise AccessRejected('최고관리자만 관리자 권한 신청을 심사할 수 있습니다.', code='main_only')
            if actor.pk == target.pk:
                raise AccessRejected('자신의 신청을 심사할 수 없습니다.', code='self_change')
            if decision not in ('APPROVED', 'REJECTED') or len(note) > 500:
                raise AccessRejected('심사 결과와 사유를 확인하세요.', code='invalid_input')
            if row.revision != revision or row.status != 'PENDING':
                raise AccessRejected('이미 심사되었거나 다른 관리자가 변경했습니다.', code='conflict')
            if decision == 'REJECTED' and not note.strip():
                raise AccessRejected('거절 사유를 입력하세요.', code='invalid_input')
            if decision == 'APPROVED':
                change_access(actor, target.pk, new_roles=roles(target)|{'SUB_ADMIN'}, reason='approved_admin_application')
            row.status = decision
            row.decision_note = note.strip()
            row.reviewed_by = actor
            row.reviewed_at = timezone.now()
            row.revision += 1
            row.save()
            audit(actor, target, 'admin.request_reviewed', {'status': 'PENDING'}, {'status': decision})
            return row
    except AccessRejected as exc:
        audit(actor, target, 'admin.request_denied', result='DENIED', reason=exc.code or 'invalid')
        raise
