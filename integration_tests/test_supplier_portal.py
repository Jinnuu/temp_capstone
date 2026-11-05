import io
from datetime import timedelta
from decimal import Decimal
from django.contrib.auth import get_user_model
from django.core.exceptions import PermissionDenied
from django.test import TestCase, Client, override_settings
from django.urls import reverse
from django.utils import timezone
import openpyxl
from accounts.models import AccessAudit, AdminRoleRequest, Announcement
from accounts.rbac import roles, can, is_main
from accounts.access_service import set_roles, change_access, AccessRejected
from accounts.admin_requests import submit_request, review_request
from procurement.models import Supplier, SupplierMembership, PurchaseOrder, OrderItem, SupplierFulfillment, SupplierDeliveryLine
from procurement.portal_services import review_membership, update_fulfillment, verified_membership
from procurement.workflow import inspect_item
from inventory.models import Ingredient, InventoryLog

User=get_user_model()
PW='Fresh-Test-Only-Password-492!'

class PortalContracts(TestCase):
    def setUp(self):
        self.main=User.objects.create_superuser('fresh-main','main@example.invalid',PW,name='최고관리자')
        self.sub=self.make('fresh-sub','NUTRITIONIST',{'SUB_ADMIN'})
        self.vendor=self.make('fresh-a','SUPPLIER',{'SUPPLIER'})
        self.other=self.make('fresh-b','SUPPLIER',{'SUPPLIER'})
        self.dietitian=self.make('fresh-dietitian','NUTRITIONIST',{'DIETITIAN'})
        self.profile=Supplier.objects.create(name='신선 A 식품',category='농산물',user=self.vendor)
        self.profile_b=Supplier.objects.create(name='격리 B 식품',category='농산물',user=self.other)
        self.member=SupplierMembership.objects.create(account=self.vendor,supplier=self.profile,requested_company=self.profile.name,contact_name='A 담당',contact_phone='02-0000-0000',status='VERIFIED')
        SupplierMembership.objects.create(account=self.other,supplier=self.profile_b,requested_company=self.profile_b.name,contact_name='B 담당',contact_phone='02-0000-0000',status='VERIFIED')
        self.ingredient=Ingredient.objects.create(name='신선 A 재료',unit='kg',safe_stock_level=0,unit_price=100,supplier=self.vendor)
        self.order=PurchaseOrder.objects.create(supplier=self.vendor,total_amount=1000,status='승인')
        self.item=OrderItem.objects.create(purchase_order=self.order,ingredient=self.ingredient,required_qty=10,missing_qty=10,order_unit_price=100,estimated_price=1000,target_date=timezone.localdate(),meal_type='',package_quantity=2,order_unit='봉',spec_snapshot='5kg/봉')
        self.order_b=PurchaseOrder.objects.create(supplier=self.other,total_amount=2345)
        OrderItem.objects.create(purchase_order=self.order_b,ingredient=self.ingredient,required_qty=23,missing_qty=23,order_unit_price=100,estimated_price=2300,target_date=timezone.localdate(),meal_type='')
        self.client.force_login(self.vendor)

    def make(self,name,kind,assigned):
        user=User.objects.create_user(name,email=name+'@example.invalid',password=PW,name=name,role=kind,is_active=True,rbac_managed=True,account_state='ACTIVE')
        set_roles(user,assigned)
        return user

    def step(self,state,revision,**kwargs):
        return update_fulfillment(self.vendor,self.order.pk,state=state,revision=revision,**kwargs)

    def test_dietitian_signup_auto_no_admin(self):
        with override_settings(ACCOUNT_APPROVAL_MODE='auto'):
            r=self.client.post(reverse('signup'),{'username':'fresh-new-d','email':'d@example.invalid','signup_type':'DIETITIAN','password1':PW,'password2':PW,'role':'MAIN_ADMIN','is_superuser':'1'})
        self.assertEqual(r.status_code,302);u=User.objects.get(username='fresh-new-d')
        self.assertTrue(u.is_active);self.assertEqual(roles(u),{'DIETITIAN'});self.assertFalse(u.is_superuser)

    def test_supplier_signup_requires_company_and_contact(self):
        data={'username':'fresh-new-s','email':'s@example.invalid','signup_type':'SUPPLIER','password1':PW,'password2':PW}
        self.assertEqual(self.client.post(reverse('signup'),data).status_code,200)
        self.assertFalse(User.objects.filter(username='fresh-new-s').exists())
        with override_settings(ACCOUNT_APPROVAL_MODE='auto'):
            self.assertEqual(self.client.post(reverse('signup'),{**data,'company_name':'신청 업체','contact_name':'담당자','contact_phone':'02-0000-0000'}).status_code,302)
        u=User.objects.get(username='fresh-new-s');self.assertEqual(roles(u),{'SUPPLIER'});self.assertTrue(u.is_active)
        self.assertEqual(u.portal_membership.status,'PENDING');self.assertIsNone(u.portal_membership.supplier_id)
        self.assertFalse(Supplier.objects.filter(name='신청 업체').exists())
        self.client.logout();self.assertTrue(self.client.login(username=u.username,password=PW))
        self.assertContains(self.client.get(reverse('procurement:portal_home')),'소속 확인')
        self.assertEqual(self.client.get(reverse('procurement:portal_orders')).status_code,403)

    def test_signup_invalid_type_cannot_gain_roles(self):
        for kind in ('MAIN_ADMIN','SUB_ADMIN','SYSTEM_ADMIN','invented'):
            r=self.client.post(reverse('signup'),{'username':'forge-'+kind,'email':'x@example.invalid','signup_type':kind,'password1':PW,'password2':PW})
            self.assertEqual(r.status_code,200);self.assertFalse(User.objects.filter(username='forge-'+kind).exists())

    def test_role_landing_and_workspaces(self):
        self.assertEqual(self.client.get('/').url,reverse('procurement:portal_home'))
        self.client.logout();r=self.client.post(reverse('login'),{'username':self.vendor.username,'password':PW})
        self.assertEqual(r.url,reverse('procurement:portal_home'))
        for user,expected in [(self.main,'account_admin_dashboard'),(self.sub,'account_admin_dashboard'),(self.dietitian,'home')]:
            self.client.logout();r=self.client.post(reverse('login'),{'username':user.username,'password':PW})
            self.assertEqual(r.url,reverse(expected))

    def test_supplier_cannot_access_internal_views_or_api(self):
        for url in ['/inventory/ingredients/','/meals/mealplan_create/','/procurement/orders/','/procurement/workflow/','/accounts/manage/']:
            self.assertEqual(self.client.get(url).status_code,403,url)
        self.assertEqual(self.client.post('/meals/api/menus/add/',{}).status_code,403)

    def test_order_list_json_search_and_sort_scoped(self):
        url=reverse('procurement:portal_orders')
        response=self.client.get(url,{'format':'json','supplier_id':self.other.pk,'sort':'oldest'})
        self.assertEqual([o['id'] for o in response.json()['orders']],[self.order.pk])
        self.assertNotContains(self.client.get(url),'2345')
        self.assertEqual(self.client.get(url,{'format':'json','q':self.order_b.pk}).json()['orders'],[])

    def test_idor_detail_json_export_and_post_all_denied(self):
        for name in ('portal_detail','portal_export'):
            url=reverse('procurement:'+name,args=[self.order_b.pk])
            self.assertEqual(self.client.get(url).status_code,404)
            self.assertEqual(self.client.get(url,{'format':'json','supplier_id':self.vendor.pk}).status_code,404)
        self.assertEqual(self.client.post(reverse('procurement:portal_detail',args=[self.order_b.pk]),{'state':'ACCEPTED','revision':0}).status_code,404)
        with self.assertRaises(PurchaseOrder.DoesNotExist):update_fulfillment(self.vendor,self.order_b.pk,state='ACKNOWLEDGED',revision=0)

    def test_download_reuses_vendor_export_only_owned_order(self):
        # Same-vendor second order must not appear in this single-order export either.
        extra=PurchaseOrder.objects.create(supplier=self.vendor,total_amount=9876)
        secret=Ingredient.objects.create(name='같은 업체의 다른 발주',unit='kg',safe_stock_level=0,unit_price=1)
        OrderItem.objects.create(purchase_order=extra,ingredient=secret,required_qty=1,missing_qty=1,order_unit_price=1,estimated_price=1,target_date=timezone.localdate(),meal_type='')
        r=self.client.get(reverse('procurement:portal_export',args=[self.order.pk]),{'supplier_id':self.other.pk})
        self.assertEqual(r.status_code,200)
        ws=openpyxl.load_workbook(io.BytesIO(r.content)).active
        text=str(list(ws.values));self.assertIn('신선 A 재료',text);self.assertNotIn('같은 업체의 다른 발주',text);self.assertEqual(ws.max_row,2)

    def test_pending_membership_denies_all_data_routes(self):
        self.member.status='PENDING';self.member.save()
        for url in [reverse('procurement:portal_orders'),reverse('procurement:portal_detail',args=[self.order.pk]),reverse('procurement:portal_export',args=[self.order.pk])]:
            self.assertEqual(self.client.get(url).status_code,403)
        self.assertContains(self.client.get(reverse('procurement:portal_home')),'발주서·수주 데이터를 볼 수 없습니다')

    def test_shared_company_accounts_reuse_legacy_owner(self):
        account=self.make('company-colleague','SUPPLIER',{'SUPPLIER'})
        member=SupplierMembership.objects.create(account=account,requested_company=self.profile.name,contact_name='동료',contact_phone='000')
        review_membership(self.sub,member.pk,self.profile.pk,0,note='외부 연락으로 담당자 확인')
        self.client.force_login(account)
        self.assertEqual(self.client.get(reverse('procurement:portal_detail',args=[self.order.pk])).status_code,200)
        self.order.refresh_from_db();self.assertEqual(self.order.supplier_id,self.vendor.pk)
        self.assertFalse(can(account,'inventory.write'))

    def test_membership_self_approval_and_staff_forgery_denied(self):
        set_roles(self.vendor,{'SUPPLIER','SUB_ADMIN'})
        with self.assertRaises(AccessRejected):review_membership(self.vendor,self.member.pk,self.profile.pk,0,note='self')
        self.client.force_login(self.dietitian)
        self.assertEqual(self.client.post(reverse('procurement:membership_reviews'),{'membership':self.member.pk,'supplier':self.profile.pk,'revision':0,'is_superuser':1}).status_code,403)

    def test_membership_duplicate_company_create_rejected(self):
        account=self.make('new-company','SUPPLIER',{'SUPPLIER'})
        member=SupplierMembership.objects.create(account=account,requested_company=self.profile.name,contact_name='담당',contact_phone='000')
        with self.assertRaises(AccessRejected):review_membership(self.main,member.pk,None,0,create_company=True,note='확인')
        self.assertEqual(Supplier.objects.filter(name=self.profile.name).count(),1)

    def test_new_company_approved_explicitly_without_credentials_change(self):
        account=self.make('new-company2','SUPPLIER',{'SUPPLIER'})
        original=(account.password,account.email,account.role)
        member=SupplierMembership.objects.create(account=account,requested_company='검증 신규 업체',contact_name='담당',contact_phone='000')
        review_membership(self.main,member.pk,None,0,create_company=True,note='사업자와 담당자 연락으로 확인')
        account.refresh_from_db();member.refresh_from_db()
        self.assertEqual((account.password,account.email,account.role),original);self.assertEqual(member.supplier.user_id,account.pk)

    def test_membership_changes_require_admin_and_revision(self):
        colleague=self.make('changing-employee','SUPPLIER',{'SUPPLIER'})
        member=SupplierMembership.objects.create(account=colleague,supplier=self.profile,status='VERIFIED',requested_company=self.profile.name,contact_name='직원',contact_phone='000',registered_via_portal=True)
        self.client.force_login(colleague)
        with self.assertRaises(AccessRejected):review_membership(self.dietitian,member.pk,self.profile_b.pk,0,note='변경')
        review_membership(self.main,member.pk,self.profile_b.pk,0,note='새 소속 확인')
        with self.assertRaises(AccessRejected):review_membership(self.main,member.pk,self.profile.pk,0,note='오래된 요청')
        self.assertEqual(self.client.get(reverse('procurement:portal_detail',args=[self.order.pk])).status_code,404)
        self.assertEqual(self.client.get(reverse('procurement:portal_detail',args=[self.order_b.pk])).status_code,200)

    def test_state_machine_does_not_modify_order_or_stock(self):
        self.step('ACKNOWLEDGED',0)
        when=timezone.localdate()+timedelta(days=1)
        for state,rev in [('ACCEPTED',1),('PREPARING',2),('DISPATCHED',3)]:
            self.step(state,rev,delivery_date=when,quantities={str(self.item.pk):'8.5'})
        self.assertFalse(InventoryLog.objects.exists());self.assertFalse(self.order.items.filter(inspection__isnull=False).exists())
        self.order.refresh_from_db();self.item.refresh_from_db();self.assertEqual(self.order.status,'승인');self.assertEqual(self.item.required_qty,10)
        self.assertEqual(self.item.delivery_plan.planned_quantity,Decimal('8.5'))

    def test_rejection_requires_reason_terminal_and_not_buyer_cancel(self):
        with self.assertRaises(AccessRejected):self.step('REJECTED',0)
        self.step('REJECTED',0,rejection_reason='납품할 수 없음')
        with self.assertRaises(AccessRejected):self.step('ACCEPTED',1,delivery_date=timezone.localdate())
        self.assertFalse(InventoryLog.objects.exists());self.order.refresh_from_db();self.assertEqual(self.order.status,'승인')

    def test_invalid_transition_and_duplicate_revision_rejected(self):
        with self.assertRaises(AccessRejected):self.step('DISPATCHED',0)
        self.step('ACKNOWLEDGED',0)
        with self.assertRaises(AccessRejected):self.step('ACKNOWLEDGED',0)
        self.assertEqual(SupplierFulfillment.objects.get(order=self.order).revision,1)

    def test_delivery_bad_dates_and_quantities(self):
        for date_value,amount in [(None,1),(timezone.localdate()-timedelta(days=1),1),(timezone.localdate(),'-1'),(timezone.localdate(),'NaN'),(timezone.localdate(),'11'),(timezone.localdate(),'0.0000001')]:
            with self.assertRaises(AccessRejected):self.step('ACCEPTED',0,delivery_date=date_value,quantities={str(self.item.pk):amount})
        self.assertFalse(SupplierFulfillment.objects.exists())

    def test_other_item_and_inventory_fields_are_rejected(self):
        with self.assertRaises(AccessRejected):self.step('ACCEPTED',0,delivery_date=timezone.localdate(),quantities={'999999':'5'})
        url=reverse('procurement:portal_detail',args=[self.order.pk])
        r=self.client.post(url,{'state':'ACKNOWLEDGED','revision':0,'accepted_qty':'100','supplier':self.other.pk})
        self.assertEqual(r.status_code,400);self.assertFalse(InventoryLog.objects.exists())

    def test_acceptance_edits_allowed_only_before_dispatch_or_inspection(self):
        self.step('ACCEPTED',0,delivery_date=timezone.localdate(),quantities={str(self.item.pk):5})
        self.step('ACCEPTED',1,delivery_date=timezone.localdate()+timedelta(days=1),quantities={str(self.item.pk):6})
        inspect_item(self.item.pk,self.dietitian,6,5,'정상','5kg/봉',notes='부분 납품 및 합격 차이 확인')
        self.assertEqual(InventoryLog.objects.get().quantity,5)
        with self.assertRaises(AccessRejected):self.step('PREPARING',2,delivery_date=timezone.localdate(),quantities={str(self.item.pk):6})
        inspect_item(self.item.pk,self.dietitian,6,5,'정상','5kg/봉',notes='부분 납품 및 합격 차이 확인')
        self.assertEqual(InventoryLog.objects.count(),1)

    def test_buyer_sees_delivery_plan_not_auto_accepted_quantity(self):
        self.step('ACCEPTED',0,delivery_date=timezone.localdate(),quantities={str(self.item.pk):8})
        self.client.force_login(self.dietitian)
        r=self.client.get(reverse('procurement:workflow_inspection',args=[self.item.pk]))
        self.assertContains(r,'공급업체 수주·납품 정보');self.assertContains(r,'8.000000')
        self.assertFalse(InventoryLog.objects.exists())

    def test_portal_csrf_and_unauthorized_api_calls(self):
        secure=Client(enforce_csrf_checks=True);secure.force_login(self.vendor)
        self.assertEqual(secure.post(reverse('procurement:portal_detail',args=[self.order.pk]),{'state':'ACKNOWLEDGED','revision':0}).status_code,403)
        self.client.force_login(self.dietitian)
        self.assertEqual(self.client.get(reverse('procurement:portal_orders'),{'format':'json'}).status_code,403)

    def test_dashboard_counts_are_real_and_company_scoped(self):
        r=self.client.get(reverse('procurement:portal_home'));self.assertEqual(r.context['counts']['new'],1)
        self.step('ACCEPTED',0,delivery_date=timezone.localdate(),quantities={str(self.item.pk):10})
        r=self.client.get(reverse('procurement:portal_home'));self.assertEqual(r.context['counts']['scheduled'],1);self.assertEqual(r.context['counts']['new'],0)

    def test_admin_request_preserves_login_roles_and_rejects_forgery(self):
        original=(self.vendor.password,self.vendor.is_active,roles(self.vendor))
        row=submit_request(self.vendor,'공급업체 담당자로 내부 운영 관리 권한을 신청합니다')
        self.vendor.refresh_from_db();self.assertEqual((self.vendor.password,self.vendor.is_active,roles(self.vendor)),original)
        r=self.client.post(reverse('admin_request'),{'reason':'권한 요청','role':'MAIN_ADMIN','is_staff':'1'})
        self.assertEqual(r.status_code,400);self.assertFalse(can(self.vendor,'accounts.manage'))

    def test_main_approves_supplier_sub_admin_and_can_revoke(self):
        row=submit_request(self.vendor,'겸임 관리 업무 승인 요청')
        review_request(self.main,row.pk,'APPROVED',0,note='내부 운영 담당 확인')
        self.vendor.refresh_from_db();self.assertEqual(roles(self.vendor),{'SUPPLIER','SUB_ADMIN'});self.assertTrue(can(self.vendor,'accounts.manage'));self.assertFalse(self.vendor.is_staff)
        self.assertFalse(can(self.vendor,'inventory.write'));self.assertFalse(can(self.vendor,'inspection.write'))
        from django.core.exceptions import ValidationError
        with self.assertRaises(ValidationError):inspect_item(self.item.pk,self.vendor,10,10,'정상','5kg/봉')
        self.assertEqual(self.client.post(reverse('procurement:workflow_transaction'),{}).status_code,403)
        self.assertEqual(self.client.get(reverse('procurement:portal_detail',args=[self.order_b.pk])).status_code,404)
        change_access(self.main,self.vendor.pk,new_roles={'SUPPLIER'})
        self.vendor.refresh_from_db();self.assertFalse(can(self.vendor,'accounts.manage'));self.assertTrue(can(self.vendor,'portal.read'))

    def test_main_rejects_request_keeps_general_account(self):
        row=submit_request(self.dietitian,'관리자 업무 신청')
        review_request(self.main,row.pk,'REJECTED',0,note='현재 역할로 업무 가능')
        self.assertEqual(roles(User.objects.get(pk=self.dietitian.pk)),{'DIETITIAN'})
        self.assertTrue(User.objects.get(pk=self.dietitian.pk).is_active)

    def test_sub_cannot_review_requests_or_grant_admin_aliases(self):
        row=submit_request(self.dietitian,'관리자 업무 신청')
        with self.assertRaises(AccessRejected):review_request(self.sub,row.pk,'APPROVED',0)
        for assigned in ({'MAIN_ADMIN'},{'SUB_ADMIN'},{'SYSTEM_ADMIN'}):
            with self.assertRaises(AccessRejected):change_access(self.sub,self.dietitian.pk,new_roles=assigned)
        self.client.force_login(self.sub)
        self.assertEqual(self.client.get(reverse('account_admin_requests')).status_code,403)
        self.assertEqual(self.client.post(reverse('account_admin_review',args=[row.pk]),{'decision':'APPROVED','revision':0}).status_code,403)

    def test_sub_cannot_manage_main_other_sub_or_self(self):
        for target in (self.main,self.sub):
            with self.assertRaises(AccessRejected):change_access(self.sub,target.pk,state='SUSPENDED')
            self.client.force_login(self.sub)
            self.assertEqual(self.client.get(reverse('account_admin_detail',args=[target.pk])).status_code,403)
            self.assertEqual(self.client.get(reverse('account_admin_api',args=[target.pk])).status_code,403)
        r=self.client.get(reverse('account_admin_users'));listed={user.pk for user in r.context['records']};self.assertNotIn(self.main.pk,listed);self.assertNotIn(self.sub.pk,listed)

    def test_sub_can_manage_general_roles_and_state(self):
        change_access(self.sub,self.dietitian.pk,new_roles={'VIEWER','COOK'})
        change_access(self.sub,self.dietitian.pk,state='SUSPENDED')
        self.dietitian.refresh_from_db();self.assertFalse(self.dietitian.is_active);self.assertEqual(roles(self.dietitian),{'VIEWER','COOK'})

    def test_admin_request_review_revision_and_duplicate_protection(self):
        row=submit_request(self.dietitian,'관리자 신청');same=submit_request(self.dietitian,'중복 신청')
        self.assertEqual(row.pk,same.pk)
        review_request(self.main,row.pk,'APPROVED',0)
        with self.assertRaises(AccessRejected):review_request(self.main,row.pk,'REJECTED',0,note='중복')
        self.assertTrue(can(User.objects.get(pk=self.dietitian.pk),'accounts.manage'))

    def test_legacy_system_admin_alias_preserves_main_not_staff_promotion(self):
        set_roles(self.dietitian,{'SYSTEM_ADMIN'});self.assertTrue(is_main(self.dietitian))
        self.assertFalse(self.dietitian.is_staff);self.assertFalse(self.dietitian.is_superuser)

    def test_main_last_and_self_protected(self):
        self.main.is_active=False;self.main.save();set_roles(self.sub,{'MAIN_ADMIN'})
        with self.assertRaises(AccessRejected):change_access(self.sub,self.sub.pk,new_roles={'VIEWER'})
        self.assertTrue(is_main(User.objects.get(pk=self.sub.pk)))

    def test_sub_audit_scope_excludes_admin_security_history(self):
        from accounts.access_service import audit
        audit(self.main,self.main,'policy.example',after={'roles':['MAIN_ADMIN']})
        change_access(self.main,self.dietitian.pk,new_roles={'VIEWER'})
        self.client.force_login(self.sub);r=self.client.get(reverse('account_admin_audit'))
        self.assertNotContains(r,'policy.example');self.assertContains(r,'account.changed')

    def test_green_civic_reference_dashboard_data_not_fake(self):
        self.client.force_login(self.dietitian)
        Announcement.objects.create(title='검증 공지',message='실제 DB 공지',author=self.main)
        r=self.client.get('/')
        self.assertContains(r,'fresh-produce-original.png');self.assertContains(r,'실제 DB 공지')
        self.assertEqual(r.context['inspection_pending_count'],2)
        for name in ('account_admin_dashboard','account_admin_matrix'):
            self.client.force_login(self.sub);self.assertEqual(self.client.get(reverse(name)).status_code,200)

    def test_linked_supplier_profile_delete_is_graceful_and_preserved(self):
        self.client.force_login(self.main)
        r=self.client.post(reverse('procurement:supplier_delete',args=[self.profile.pk]),follow=True)
        self.assertContains(r,'포털 계정이 연결된 거래처는 삭제할 수 없습니다')
        self.assertTrue(Supplier.objects.filter(pk=self.profile.pk).exists())

    def test_sub_cannot_access_native_admin_or_security_policy_post(self):
        self.client.force_login(self.sub)
        self.assertEqual(self.client.get('/admin/').status_code,403)
        self.assertEqual(self.client.post(reverse('account_admin_matrix'),{'ACCOUNT_APPROVAL_MODE':'auto'}).status_code,405)

    def test_role_migration_does_not_restore_previously_demoted_legacy_admin(self):
        import importlib
        from types import SimpleNamespace
        from django.apps import apps
        from django.db import connection
        demoted=self.make('demoted-legacy','ADMIN',{'VIEWER'})
        importlib.import_module('procurement.migrations.0011_initialize_portal_roles').initialize(apps,SimpleNamespace(connection=connection))
        demoted.refresh_from_db();self.assertEqual(roles(demoted),{'VIEWER'});self.assertFalse(is_main(demoted))
        self.assertTrue(is_main(User.objects.get(pk=self.main.pk)))

    def test_legacy_completed_orders_are_read_only_without_invented_supplier_history(self):
        for status in ('완료','배송완료'):
            self.order.status=status;self.order.save()
            r=self.client.get(reverse('procurement:portal_detail',args=[self.order.pk]))
            self.assertContains(r,'기존 검수 완료')
            self.assertNotContains(r,'name="state"')
            response=self.client.get(reverse('procurement:portal_detail',args=[self.order.pk]),{'format':'json'})
            self.assertIsNone(response.json()['state'])
            self.assertFalse(SupplierFulfillment.objects.filter(order=self.order).exists())


    def test_portal_employee_is_not_a_separate_order_counterparty(self):
        from accounts.supplier_identity import eligible_order_accounts
        from inventory.forms import IngredientForm
        from procurement.workflow_forms import SpecificationForm
        employee=self.make('portal-employee','SUPPLIER',{'SUPPLIER'})
        member=SupplierMembership.objects.create(account=employee,requested_company=self.profile.name,contact_name='직원',contact_phone='000',registered_via_portal=True)
        self.assertNotIn(employee.pk,eligible_order_accounts().values_list('pk',flat=True))
        review_membership(self.main,member.pk,self.profile.pk,0,note='기존 업체 직원 확인')
        self.assertNotIn(employee.pk,IngredientForm().fields['supplier'].queryset.values_list('pk',flat=True))
        self.assertNotIn(employee.pk,SpecificationForm().fields['supplier'].queryset.values_list('pk',flat=True))
        self.assertIn(self.vendor.pk,eligible_order_accounts().values_list('pk',flat=True))

    def test_canonical_order_account_cannot_be_reassigned_to_another_company(self):
        with self.assertRaises(AccessRejected):review_membership(self.main,self.member.pk,self.profile_b.pk,0,note='변경 요청')
        self.member.refresh_from_db();self.assertEqual(self.member.supplier_id,self.profile.pk)
        self.order.refresh_from_db();self.assertEqual(self.order.supplier_id,self.vendor.pk)

    def test_new_company_owner_becomes_eligible_after_explicit_approval_only(self):
        from accounts.supplier_identity import eligible_order_accounts
        user=self.make('portal-new-owner','SUPPLIER',{'SUPPLIER'})
        member=SupplierMembership.objects.create(account=user,requested_company='독립 신규 회사',contact_name='담당',contact_phone='000',registered_via_portal=True)
        self.assertFalse(eligible_order_accounts().filter(pk=user.pk).exists())
        review_membership(self.main,member.pk,None,0,create_company=True,note='신규 업체 실재 확인')
        self.assertTrue(eligible_order_accounts().filter(pk=user.pk).exists())



from django.test import TransactionTestCase, skipUnlessDBFeature
from concurrent.futures import ThreadPoolExecutor
from django.db import close_old_connections

class PortalConcurrencyContracts(TransactionTestCase):
    @skipUnlessDBFeature('has_select_for_update')
    def test_duplicate_supplier_actions_only_commit_once(self):
        import threading
        from accounts.models import AccessPolicy
        AccessPolicy.objects.get_or_create(pk=1)
        user=User.objects.create_user('parallel-supplier',name='동시 수주',role='SUPPLIER',rbac_managed=True,account_state='ACTIVE',is_active=True)
        set_roles(user,{'SUPPLIER'})
        profile=Supplier.objects.create(user=user,name='동시 업체',category='농산물')
        SupplierMembership.objects.create(account=user,supplier=profile,status='VERIFIED',requested_company='동시 업체',contact_name='담당',contact_phone='000')
        ingredient=Ingredient.objects.create(name='동시 재료',unit='kg',safe_stock_level=0,unit_price=1)
        order=PurchaseOrder.objects.create(supplier=user,status='승인')
        OrderItem.objects.create(purchase_order=order,ingredient=ingredient,required_qty=1,missing_qty=1,order_unit_price=1,estimated_price=1)
        barrier=threading.Barrier(2)
        def submit(_):
            close_old_connections()
            try:
                actor=User.objects.get(pk=user.pk);barrier.wait(timeout=10)
                update_fulfillment(actor,order.pk,state='ACKNOWLEDGED',revision=0)
                return 'changed'
            except AccessRejected:return 'conflict'
            finally:close_old_connections()
        with ThreadPoolExecutor(max_workers=2) as pool:result=list(pool.map(submit,[1,2]))
        self.assertEqual(sorted(result),['changed','conflict'])
        self.assertEqual(SupplierFulfillment.objects.get(order=order).revision,1)
        self.assertFalse(InventoryLog.objects.exists())
