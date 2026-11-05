"""Fixed-role authorization and audited approval, with real session/HTTP checks."""
import json
from io import StringIO
from django.contrib.auth import get_user_model
from django.core.management import call_command
from django.test import TestCase, override_settings, Client
from django.urls import reverse
from accounts.models import AccessAudit, AccessPolicy
from accounts.rbac import can, roles, account_can_login, required_capability, ROLE_CAPS
from accounts.access_service import register, change_access, set_roles, classify_signup, AccessRejected, sync_policy

User=get_user_model()


class AccountAccessTests(TestCase):
    def setUp(self):
        self.admin=User.objects.create_superuser('rbac-admin', 'admin@example.invalid', 'Test-Only-Password-42', name='관리자')
        self.other=User.objects.create_user('rbac-other', password='Test-Only-Password-42', name='영양사')
        register(self.other)
        self.other.account_state='ACTIVE';self.other.is_active=True;self.other.save()
        self.client.force_login(self.admin)

    def assign(self, user, names):
        user.rbac_managed=True;user.account_state='ACTIVE';user.is_active=True;user.save();set_roles(user,names)

    def test_manual_signup_pending_and_audited(self):
        with override_settings(ACCOUNT_APPROVAL_MODE='manual'):
            user=register(User(username='pending',name='대기'))
        self.assertFalse(user.is_active);self.assertEqual(user.account_state,'PENDING')
        self.assertEqual(roles(user),{'DIETITIAN'})
        self.assertTrue(AccessAudit.objects.filter(target=user,action='signup.pending').exists())

    @override_settings(ACCOUNT_APPROVAL_MODE='auto')
    def test_auto_signup_immediate_login_without_privilege_escalation(self):
        self.assertContains(self.client.get(reverse('signup')), '회원가입 후 바로 로그인')
        response=self.client.post(reverse('signup'),{'username':'auto-new','email':'new@example.invalid','password1':'Example-Safe-Password-422','password2':'Example-Safe-Password-422','is_superuser':'1','roles':['SYSTEM_ADMIN']})
        self.assertEqual(response.status_code,302)
        user=User.objects.get(username='auto-new')
        self.assertTrue(account_can_login(user));self.assertFalse(user.is_staff);self.assertFalse(user.is_superuser)
        self.assertEqual(roles(user),{'DIETITIAN'})
        self.client.logout();self.assertTrue(self.client.login(username=user.username,password='Example-Safe-Password-422'))
        self.assertEqual(self.client.get('/').status_code,200)

    def test_confirmed_pending_approval_idempotent_preserves_identity(self):
        self.other.account_state='LEGACY_INACTIVE';self.other.is_active=False;self.other.save()
        original=(self.other.password,self.other.email,self.other.role,self.other.is_staff)
        classify_signup(self.admin,self.other.pk)
        user,changed=change_access(self.admin,self.other.pk,state='ACTIVE')
        self.assertTrue(changed)
        _,changed=change_access(self.admin,self.other.pk,state='ACTIVE');self.assertFalse(changed)
        self.assertEqual(original,(user.password,user.email,user.role,user.is_staff))

    def test_suspended_and_unknown_never_classified_as_signup(self):
        for state in ('SUSPENDED','DISABLED','WITHDRAWN'):
            self.other.account_state=state;self.other.is_active=False;self.other.save()
            with self.assertRaises(AccessRejected):classify_signup(self.admin,self.other.pk)
        self.other.account_state='LEGACY_INACTIVE';self.other.save()
        with self.assertRaises(AccessRejected):change_access(self.admin,self.other.pk,state='ACTIVE')

    def test_preview_command_guard(self):
        with self.assertRaises(Exception):call_command('approve_preview_signups',actor=self.admin.username,confirmed_signup=[self.other.username],stdout=StringIO())

    @override_settings(SNP_UI_PREVIEW=True,ACCOUNT_APPROVAL_MODE='auto')
    def test_preview_command_only_confirmed_target_and_rerun(self):
        self.other.account_state='LEGACY_INACTIVE';self.other.is_active=False;self.other.save()
        unknown=User.objects.create_user('untouched',is_active=False,name='확인 필요',rbac_managed=True)
        for _ in range(2):call_command('approve_preview_signups',actor=self.admin.username,confirmed_signup=[self.other.username],stdout=StringIO())
        self.other.refresh_from_db();unknown.refresh_from_db()
        self.assertTrue(self.other.is_active);self.assertFalse(unknown.is_active)
        self.assertEqual(AccessAudit.objects.filter(target=self.other,action='account.changed').count(),1)

    def test_suspended_login_and_existing_session_blocked(self):
        self.client.force_login(self.other)
        change_access(self.admin,self.other.pk,state='SUSPENDED')
        self.assertEqual(self.client.get('/').status_code,302)
        self.assertFalse(self.client.login(username=self.other.username,password='Test-Only-Password-42'))
        response=self.client.post(reverse('login'),{'username':self.other.username,'password':'Test-Only-Password-42'})
        self.assertContains(response,'사용이 중지')

    def test_regular_user_admin_pages_and_direct_api_denied_audited(self):
        self.client.force_login(self.other)
        for url in [reverse('account_admin_users'),reverse('account_admin_matrix'),reverse('account_admin_audit'),reverse('account_admin_detail',args=[self.admin.pk]),reverse('account_admin_api',args=[self.admin.pk]),'/admin/']:
            self.assertEqual(self.client.get(url).status_code,403,url)
        self.assertEqual(self.client.post(reverse('account_admin_api',args=[self.admin.pk]),json.dumps({'state':'ACTIVE','roles':['SYSTEM_ADMIN'],'revision':0}),content_type='application/json').status_code,403)
        self.assertEqual(AccessAudit.objects.filter(action='admin.access_denied',result='DENIED').count(),7)

    def test_role_matrix_all_mutations_denied_to_viewer(self):
        self.assign(self.other,{'VIEWER'});self.client.force_login(self.other)
        for url in ['/meals/api/menus/add/','/meals/mealplan_create/','/procurement/workflow/','/procurement/workflow/preview/','/procurement/workflow/transactions/','/procurement/suppliers/create/','/inventory/ingredients/create/','/forecasting/predict/']:
            response=self.client.post(url,{})
            self.assertEqual(response.status_code,403,url)
        self.assertTrue(can(self.other,'inventory.read'));self.assertFalse(can(self.other,'inventory.write'))

    def test_inventory_cook_and_dietitian_capabilities(self):
        for role,yes,no in [('INVENTORY_MANAGER','inventory.write','meals.write'),('COOK','cooking.write','inventory.write'),('DIETITIAN','forecast.write','accounts.manage')]:
            self.assign(self.other,{role});self.assertTrue(can(self.other,yes));self.assertFalse(can(self.other,no))
        self.assign(self.other,{'COOK'});self.client.force_login(self.other)
        self.assertEqual(self.client.post('/meals/api/menus/add/',{}).status_code,403)

    def test_multi_roles_and_immediate_revocation(self):
        change_access(self.admin,self.other.pk,new_roles=['COOK','INVENTORY_MANAGER'],revision=0)
        self.other.refresh_from_db();self.assertTrue(can(self.other,'cooking.write'));self.assertTrue(can(self.other,'inventory.write'))
        self.client.force_login(self.other)
        change_access(self.admin,self.other.pk,new_roles=['VIEWER'],revision=1)
        self.assertEqual(self.client.post('/procurement/workflow/transactions/',{}).status_code,403)
        self.assertEqual(AccessAudit.objects.filter(target=self.other,action='account.changed').count(),2)

    def test_self_admin_and_superuser_protection(self):
        with self.assertRaises(AccessRejected):change_access(self.admin,self.admin.pk,state='SUSPENDED')
        self.assertTrue(User.objects.get(pk=self.admin.pk).is_active)
        self.assign(self.other,{'SYSTEM_ADMIN'})
        with self.assertRaises(AccessRejected):change_access(self.other,self.admin.pk,state='SUSPENDED')
        self.assertFalse(self.other.is_staff);self.assertFalse(self.other.is_superuser)

    def test_last_admin_guard_when_no_other_active_admin(self):
        self.admin.is_active=False;self.admin.save()
        self.assign(self.other,{'SYSTEM_ADMIN'})
        with self.assertRaises(AccessRejected):change_access(self.other,self.other.pk,new_roles=['VIEWER'])
        self.assertTrue(can(User.objects.get(pk=self.other.pk),'accounts.manage'))

    def test_concurrent_revision_and_invalid_role_rejected(self):
        change_access(self.admin,self.other.pk,new_roles=['VIEWER'],revision=0)
        with self.assertRaises(AccessRejected):change_access(self.admin,self.other.pk,new_roles=['SYSTEM_ADMIN'],revision=0)
        with self.assertRaises(AccessRejected):change_access(self.admin,self.other.pk,new_roles=['INVALID'],revision=1)
        self.assertEqual(roles(User.objects.get(pk=self.other.pk)),{'VIEWER'})

    def test_api_validation_csrf_and_protected_fields(self):
        url=reverse('account_admin_api',args=[self.other.pk])
        for body in [{'revision':0,'is_superuser':True},{'revision':0,'roles':'SYSTEM_ADMIN'},{'revision':0,'roles':[{}]}]:
            self.assertEqual(self.client.post(url,json.dumps(body),content_type='application/json').status_code,400)
        csrf=Client(enforce_csrf_checks=True);csrf.force_login(self.admin)
        self.assertEqual(csrf.post(url,'{}',content_type='application/json').status_code,403)

    def test_admin_ui_search_detail_matrix_and_audit(self):
        for url in [reverse('account_admin_users')+'?q=rbac',reverse('account_admin_detail',args=[self.other.pk]),reverse('account_admin_matrix'),reverse('account_admin_audit')]:
            self.assertEqual(self.client.get(url).status_code,200)
        response=self.client.post(reverse('account_admin_detail',args=[self.other.pk]),{'revision':0,'state':'ACTIVE','roles':['COOK','VIEWER']})
        self.assertEqual(response.status_code,302);self.assertEqual(roles(User.objects.get(pk=self.other.pk)),{'COOK','VIEWER'})

    def test_audit_contains_only_state_not_secrets(self):
        change_access(self.admin,self.other.pk,new_roles=['VIEWER'])
        event=AccessAudit.objects.filter(action='account.changed').latest('pk')
        self.assertEqual(event.actor,self.admin);self.assertEqual(event.target,self.other)
        self.assertEqual(event.before['roles'],['DIETITIAN']);self.assertEqual(event.after['roles'],['VIEWER'])
        serialized=json.dumps({'before':event.before,'after':event.after,'reason':event.reason})
        self.assertNotIn(self.other.password,serialized);self.assertNotIn('password',serialized)

    def test_native_admin_user_and_group_mutation_disabled(self):
        self.assertEqual(self.client.post(f'/admin/accounts/user/{self.other.pk}/change/',{'is_superuser':'on'}).status_code,403)
        self.assertEqual(self.client.post('/admin/auth/group/add/',{'name':'SNP_ROLE_SYSTEM_ADMIN'}).status_code,403)

    def test_policy_environment_audited_once(self):
        with override_settings(ACCOUNT_APPROVAL_MODE='auto'):
            sync_policy();sync_policy()
        self.assertEqual(AccessPolicy.objects.get(pk=1).mode,'auto')
        self.assertEqual(AccessAudit.objects.filter(action='policy.environment_changed').count(),1)

    def test_unknown_route_fails_closed_and_supplier_unchanged(self):
        self.assertIsNone(required_capability('unknown'))
        supplier=User.objects.create_user('rbac-supplier',role='SUPPLIER',name='업체')
        self.client.force_login(supplier);self.assertEqual(self.client.get('/').status_code,403)
        with self.assertRaises(AccessRejected):change_access(self.admin,supplier.pk,new_roles=['VIEWER'])

    def test_restore_suspended_preserves_roles_and_login(self):
        change_access(self.admin,self.other.pk,new_roles=['COOK','VIEWER'])
        change_access(self.admin,self.other.pk,state='SUSPENDED')
        change_access(self.admin,self.other.pk,state='ACTIVE')
        self.other.refresh_from_db()
        self.assertEqual(roles(self.other),{'COOK','VIEWER'})
        self.assertTrue(self.client.login(username=self.other.username,password='Test-Only-Password-42'))

    def test_active_state_with_inconsistent_flag_is_still_blocked(self):
        self.other.account_state='SUSPENDED';self.other.is_active=True;self.other.save()
        self.assertFalse(self.client.login(username=self.other.username,password='Test-Only-Password-42'))

    def test_roles_only_conversion_of_legacy_user_retains_workflow(self):
        legacy=User.objects.create_user('raw-legacy',name='기존')
        change_access(self.admin,legacy.pk,state='SUSPENDED')
        change_access(self.admin,legacy.pk,state='ACTIVE')
        legacy.refresh_from_db();self.assertEqual(roles(legacy),{'DIETITIAN'})

    def test_anonymous_management_requires_login(self):
        self.client.logout()
        self.assertEqual(self.client.get(reverse('account_admin_users')).status_code,302)
        self.assertEqual(self.client.post(reverse('account_admin_api',args=[self.other.pk]),'{}',content_type='application/json').status_code,302)


from django.db import connection, close_old_connections
from django.test import TransactionTestCase, skipUnlessDBFeature
from concurrent.futures import ThreadPoolExecutor


class AccessConcurrencyTests(TransactionTestCase):
    @skipUnlessDBFeature('has_select_for_update')
    def test_two_admins_cannot_remove_each_other_simultaneously(self):
        users=[]
        for name in ('concurrent-a','concurrent-b'):
            user=User.objects.create_user(name,name=name,is_active=True,account_state='ACTIVE',rbac_managed=True)
            set_roles(user,{'SYSTEM_ADMIN'});users.append(user)
        AccessPolicy.objects.get_or_create(pk=1)
        import threading
        barrier = threading.Barrier(2)
        def remove(pair):
            close_old_connections()
            actor_id,target_id=pair
            try:
                actor=User.objects.get(pk=actor_id)
                barrier.wait(timeout=10)
                change_access(actor,target_id,new_roles=['VIEWER'],revision=0)
                return 'changed'
            except AccessRejected:
                return 'denied'
            finally:
                close_old_connections()
        with ThreadPoolExecutor(max_workers=2) as pool:
            results=list(pool.map(remove,[(users[0].pk,users[1].pk),(users[1].pk,users[0].pk)]))
        self.assertEqual(sorted(results),['changed','denied'])
        self.assertEqual(sum(can(u,'accounts.manage') for u in User.objects.all()),1)
        self.assertEqual(AccessAudit.objects.filter(action='account.changed').count(),1)
        self.assertEqual(AccessAudit.objects.filter(action='account.change_denied',result='DENIED').count(),1)
