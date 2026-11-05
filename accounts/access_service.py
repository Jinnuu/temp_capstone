"""Audited, serialized account transitions; no password/email/legacy role writes."""
from django.contrib.auth.models import Group
from django.core.exceptions import ValidationError
from django.db import transaction
from .models import User,AccessAudit,AccessPolicy
from .rbac import PREFIX,ROLE_LABELS,roles,can,account_can_login,approval_mode,is_main,is_admin_identity


class AccessRejected(ValidationError):pass


def snapshot(user):
    return {'state':user.account_state,'active':user.is_active,'roles':sorted(roles(user)),
            'managed':user.rbac_managed,'revision':user.access_revision}


def audit(actor,target,action,before=None,after=None,result='SUCCESS',reason=''):
    return AccessAudit.objects.create(actor=actor if getattr(actor,'pk',None) else None,
        target=target,actor_label=getattr(actor,'username','SYSTEM'),target_label=getattr(target,'username',''),
        action=action,before=before or {},after=after or {},result=result,reason=reason[:300])


def policy_lock():
    AccessPolicy.objects.get_or_create(pk=1)
    return AccessPolicy.objects.select_for_update().get(pk=1)


def set_roles(user,names):
    names={'MAIN_ADMIN' if name=='SYSTEM_ADMIN' else name for name in names}
    protected=list(user.groups.filter(name__in=[PREFIX+x for x in (*ROLE_LABELS,'SYSTEM_ADMIN')]))
    user.groups.remove(*protected)
    for name in sorted(names):user.groups.add(Group.objects.get_or_create(name=PREFIX+name)[0])


def register(user, signup_type="DIETITIAN"):
    with transaction.atomic():
        user.rbac_managed=True
        user.account_state='ACTIVE' if approval_mode()=='auto' else 'PENDING'
        user.is_active=user.account_state=='ACTIVE'
        user.save();set_roles(user,{signup_type})
        audit(user,user,'signup.'+('auto_approved' if user.is_active else 'pending'),after=snapshot(user))
    return user


def sync_policy():
    with transaction.atomic():
        policy=policy_lock();new=approval_mode()
        if policy.mode!=new:
            old=policy.mode;policy.mode=new;policy.save(update_fields=['mode'])
            audit(None,None,'policy.environment_changed',{'mode':old},{'mode':new})


def change_access(actor,target_id,*,state=None,new_roles=None,revision=None,reason='administrator'):
    target=None;before={}
    try:
        with transaction.atomic():
            policy_lock()
            actor=User.objects.select_for_update().get(pk=actor.pk)
            target=User.objects.select_for_update().get(pk=target_id)
            before=snapshot(target)
            if not can(actor,'accounts.manage'):raise AccessRejected('관리자 권한이 없습니다.',code='not_admin')
            if revision is not None and revision!=target.access_revision:raise AccessRejected('다른 관리자가 수정했습니다. 새로고침 후 다시 시도하세요.',code='conflict')
            desired=set(roles(target)) if new_roles is None else {'MAIN_ADMIN' if name=='SYSTEM_ADMIN' else name for name in new_roles}
            if not is_main(actor) and (is_admin_identity(target) or desired & {'MAIN_ADMIN','SUB_ADMIN'}):
                raise AccessRejected('최고관리자만 관리자 계정을 변경할 수 있습니다.',code='admin_hierarchy')
            if target.role=='SUPPLIER':desired.add('SUPPLIER')
            if target.role!='SUPPLIER' and 'SUPPLIER' in desired:
                raise AccessRejected('공급업체 가입 유형은 역할 편집으로 변경하지 않습니다.',code='identity_type')
            if not desired.issubset(ROLE_LABELS):raise AccessRejected('정의되지 않은 역할입니다.',code='invalid_role')
            next_state=state or target.account_state
            was_managed=target.rbac_managed
            if not was_managed and target.is_active and next_state=='LEGACY_INACTIVE':next_state='ACTIVE'
            if next_state not in User.AccountState.values:raise AccessRejected('올바른 계정 상태를 선택하세요.',code='invalid_state')
            if target.account_state=='WITHDRAWN' and next_state!='WITHDRAWN':raise AccessRejected('탈퇴 계정은 이 화면에서 복구하지 않습니다.',code='withdrawn')
            if state=='ACTIVE' and target.account_state not in ('PENDING','SUSPENDED','DISABLED','ACTIVE'):
                raise AccessRejected('기존 비활성 계정은 먼저 승인 대기 여부를 확인해야 합니다.',code='unknown_state')
            if target.role=='SUPPLIER' and (desired - {'SUPPLIER','SUB_ADMIN'}):raise AccessRejected('업체 연동 계정에는 내부 업무 역할을 부여하지 않습니다.',code='supplier')
            if target.is_superuser and 'MAIN_ADMIN' not in desired:raise AccessRejected('Django 최고관리자의 시스템 관리자 역할은 회수할 수 없습니다.',code='superuser')
            changed=(desired!=roles(target) or next_state!=target.account_state)
            if not changed:return target,False
            if target.pk==actor.pk:raise AccessRejected('자신의 상태나 역할은 변경할 수 없습니다.',code='self_change')
            if target.is_superuser and not actor.is_superuser:raise AccessRejected('최고관리자 계정은 최고관리자만 변경할 수 있습니다.',code='superuser')
            admins=[u for u in User.objects.filter(is_active=True) if is_main(u)]
            remains_admin=next_state=='ACTIVE' and ('MAIN_ADMIN' in desired or target.is_superuser)
            if is_main(target) and not remains_admin and len(admins)<=1:raise AccessRejected('마지막 활성 시스템 관리자를 보호해야 합니다.',code='last_admin')
            target.account_state=next_state;target.is_active=next_state=='ACTIVE';target.rbac_managed=True;target.access_revision+=1
            target.save(update_fields=['account_state','is_active','rbac_managed','access_revision'])
            if new_roles is not None or not was_managed:set_roles(target,desired)
            after=snapshot(target)
            audit(actor,target,'account.changed',before,after,reason=reason)
            if before['state'] != after['state']:
                event = {'ACTIVE': 'account.approved_or_restored', 'SUSPENDED': 'account.suspended', 'DISABLED': 'account.disabled', 'WITHDRAWN': 'account.withdrawn'}.get(next_state, 'account.state_changed')
                audit(actor, target, event, before, after, reason=reason)
            if set(after['roles']) - set(before['roles']):
                audit(actor, target, 'roles.granted', before, after, reason=reason)
            if set(before['roles']) - set(after['roles']):
                audit(actor, target, 'roles.revoked', before, after, reason=reason)
            return target,True
    except AccessRejected as exc:
        audit(actor,target,'account.change_denied',before,before,result='DENIED',reason=exc.code or 'validation')
        raise


def classify_signup(actor,user_id):
    """Explicit operator evidence only; never infer all old inactive users as pending."""
    from django.contrib.admin.models import LogEntry
    from django.contrib.contenttypes.models import ContentType
    with transaction.atomic():
        policy_lock();actor=User.objects.get(pk=actor.pk)
        if not can(actor,'accounts.manage'):raise AccessRejected('관리자 권한이 없습니다.')
        user=User.objects.select_for_update().get(pk=user_id)
        if user.account_state in ('ACTIVE','PENDING'):return user,False
        ct=ContentType.objects.get_for_model(User)
        if user.account_state!='LEGACY_INACTIVE' or user.is_active or user.is_staff or user.is_superuser or user.role!='NUTRITIONIST' or user.last_login is not None or LogEntry.objects.filter(content_type=ct,object_id=str(user.pk)).exists():
            raise AccessRejected('가입 대기로 확인할 수 없는 계정입니다.')
        before=snapshot(user);user.account_state='PENDING';user.access_revision+=1
        user.save(update_fields=['account_state','access_revision'])
        audit(actor,user,'account.classified_pending',before,snapshot(user),reason='operator_confirmed_signup')
        return user,True
