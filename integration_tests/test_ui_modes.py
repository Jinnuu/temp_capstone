"""UI shell contracts; business calculations remain in the existing regression suite."""
from django.test import TestCase
from django.contrib.auth import get_user_model
from django.urls import reverse


class ThreeModeShell(TestCase):
    def setUp(self):
        self.user=get_user_model().objects.create_user(username='ui-shell-test',name='UI 검증',is_staff=True,role='ADMIN')
        self.client.force_login(self.user)

    def test_modes_exist_on_all_representative_screens(self):
        names=['home','meals:mealplan_list','meals:weekly_mealplan_create','meals:menu_list','forecasting:prediction_create','inventory:ingredient_list','procurement:workflow','procurement:order_list','procurement:supplier_list','procurement:workflow_ledger','meals:cooking_index','procurement:doc_monthly_settlement','procurement:workflow_categories']
        for name in names:
            with self.subTest(name=name):
                response=self.client.get(reverse(name))
                self.assertEqual(response.status_code,200)
                for mode in ['reference','green','civic']:self.assertContains(response,f'data-ui-mode="{mode}"')
                self.assertContains(response,'ui/build/snp-ui.js')
                self.assertContains(response,'ui/boot.js')

    def test_login_and_signup_also_have_mode_switcher(self):
        self.client.logout()
        for name in ['login','signup']:
            response=self.client.get(reverse(name));self.assertContains(response,'UI 모드 선택');self.assertContains(response,'snp-workspace')

    def test_compare_view_has_read_only_separate_modes(self):
        response=self.client.get(reverse('ui_compare'))
        self.assertEqual(response.status_code,200)
        for mode in ['reference','green','civic']:self.assertContains(response,f'data-snp-preview-mode="{mode}"')
        self.assertNotContains(response,'allow-forms')
        self.assertNotContains(response,'포스터 색상 확인 대기')

    def test_compare_view_respects_existing_business_auth_policy(self):
        self.client.logout();self.assertEqual(self.client.get(reverse('ui_compare')).status_code,302)
        supplier=get_user_model().objects.create_user(username='ui-supplier',name='공급업체',role='SUPPLIER')
        self.client.force_login(supplier);self.assertEqual(self.client.get(reverse('ui_compare')).status_code,403)

    def test_shell_has_skip_link_search_and_local_dependencies(self):
        response=self.client.get(reverse('home'))
        self.assertContains(response,'href="#snp-workspace"')
        self.assertContains(response,'name="search"')
        self.assertNotContains(response,'cdn.jsdelivr.net')
        self.assertContains(response,'aria-label="UI 모드 선택"')

    def test_existing_operational_navigation_and_csrf_remain(self):
        response=self.client.get(reverse('procurement:workflow'))
        for name in ['meals:recipe_upload_page','inventory:ingredient_upload','procurement:workflow_preview','procurement:workflow_inspections','meals:cooking_index','procurement:workflow_settlement']:
            self.assertContains(response,reverse(name))
        self.assertContains(response,'csrfmiddlewaretoken')

    def test_admin_keeps_its_own_permissioned_structure_with_mode_control(self):
        response=self.client.get('/admin/')
        self.assertEqual(response.status_code,200)
        self.assertContains(response,'UI 모드 선택');self.assertContains(response,'ui/admin.css')

    def test_only_explicit_preview_gets_same_origin_frame_permission(self):
        for name in ['home','procurement:workflow','inventory:ingredient_list','meals:weekly_mealplan_create','procurement:workflow_ledger','meals:cooking_index']:
            with self.subTest(name=name):
                self.assertEqual(self.client.get(reverse(name))['X-Frame-Options'], 'DENY')
                self.assertEqual(self.client.get(reverse(name), {'snp_preview':'1'})['X-Frame-Options'], 'SAMEORIGIN')

    def test_preview_flag_does_not_relax_unlisted_routes(self):
        response=self.client.get(reverse('procurement:workflow_specs'), {'snp_preview':'1'})
        self.assertEqual(response['X-Frame-Options'], 'DENY')

    def test_preview_flag_never_bypasses_authentication_or_supplier_policy(self):
        self.client.logout()
        self.assertEqual(self.client.get(reverse('home'), {'snp_preview':'1'}).status_code,302)
        supplier=get_user_model().objects.create_user(username='frame-supplier',name='업체',role='SUPPLIER')
        self.client.force_login(supplier)
        response=self.client.get(reverse('procurement:workflow'), {'snp_preview':'1'})
        self.assertEqual(response.status_code,403)
        self.assertNotEqual(response.get('X-Frame-Options'),'SAMEORIGIN')
