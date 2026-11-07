"""Guide/read progress cannot replace or mutate actual business workflows."""
from datetime import date
from django.contrib.auth import get_user_model
from django.test import TestCase
from django.urls import reverse
from accounts.access_service import set_roles
from meals.models import DietPlan
from inventory.models import InventoryLog
from procurement.models import ProcurementPlan

User=get_user_model()

class NutritionistTutorialTests(TestCase):
    def setUp(self):
        self.user=User.objects.create_user('guide-dietitian',name='합성 영양사',role='NUTRITIONIST',rbac_managed=True,account_state='ACTIVE',is_active=True)
        set_roles(self.user,{'DIETITIAN'});self.client.force_login(self.user)
        self.plan=DietPlan.objects.create(target_date=date(2026,11,6),meal_type='중식',headcount=120)

    def role_user(self, role, kind='NUTRITIONIST'):
        user=User.objects.create_user('guide-'+role.lower(),name='합성 사용자',role=kind,rbac_managed=True,account_state='ACTIVE',is_active=True)
        set_roles(user,{role});return user

    def test_old_url_is_six_step_guide_without_headcount_form(self):
        r=self.client.get(reverse('procurement:workflow'))
        self.assertContains(r,'영양사 업무 가이드')
        self.assertNotContains(r,'name="manual"')
        self.assertEqual(len(r.context['steps']),6)
        self.assertContains(r,'실제 업무 완료율이 아닙니다')

    def test_guide_get_has_no_business_writes(self):
        before=(DietPlan.objects.count(),ProcurementPlan.objects.count(),InventoryLog.objects.count())
        self.client.get(reverse('procurement:workflow'),{'completed':'6','final':'999','save':'1'})
        self.plan.refresh_from_db();self.assertEqual(self.plan.headcount,120);self.assertIsNone(self.plan.final_headcount)
        self.assertEqual(before,(DietPlan.objects.count(),ProcurementPlan.objects.count(),InventoryLog.objects.count()))

    def test_independent_headcount_screen_preserves_save_reload(self):
        url=reverse('procurement:workflow_headcounts')
        self.assertEqual(self.client.post(url,{'plan':self.plan.pk,'manual':110,'final':100,'confirm':'on'}).status_code,302)
        self.plan.refresh_from_db();self.assertEqual((self.plan.headcount,self.plan.final_headcount),(110,100))
        self.assertContains(self.client.get(url),'식수 저장')
        self.assertContains(self.client.get(url),'100')

    def test_legacy_post_still_saves_without_reimplementing_logic(self):
        r=self.client.post(reverse('procurement:workflow'),{'plan':self.plan.pk,'manual':0,'final':0,'confirm':'on'})
        self.assertRedirects(r,reverse('procurement:workflow_headcounts'))
        self.plan.refresh_from_db();self.assertEqual(self.plan.final_headcount,0)

    def test_saved_plans_are_accessible_with_review_state(self):
        saved=ProcurementPlan.objects.create(start_date=self.plan.target_date,end_date=self.plan.target_date,created_by=self.user,meal_ids=[self.plan.pk],source_fingerprint='test',needs_review=True)
        r=self.client.get(reverse('procurement:workflow_plans'))
        self.assertContains(r,reverse('procurement:workflow_plan',args=[saved.pk]));self.assertContains(r,'재검토')

    def test_new_entries_are_linked_in_navigation_and_guide(self):
        r=self.client.get(reverse('procurement:workflow'))
        for name in ['procurement:workflow_headcounts','procurement:workflow_plans','procurement:workflow_preview','procurement:workflow_inspections','procurement:workflow_ledger','meals:cooking_index','procurement:workflow_settlement']:
            self.assertContains(r,reverse(name))

    def test_viewer_sees_read_links_but_not_write_entries(self):
        self.client.force_login(self.role_user('VIEWER'))
        r=self.client.get(reverse('procurement:workflow'));self.assertEqual(r.status_code,200)
        urls={link['url'] for step in r.context['steps'] for link in step['links']}
        self.assertNotIn(reverse('meals:mealplan_create'),urls)
        self.assertNotIn(reverse('forecasting:prediction_create'),urls)
        self.assertEqual(self.client.post(reverse('procurement:workflow_headcounts'),{'plan':self.plan.pk,'manual':999}).status_code,403)
        self.assertNotContains(self.client.get(reverse('procurement:workflow_headcounts')),'name="manual"')

    def test_cook_can_read_relevant_guide_without_forecast_or_procurement_buttons(self):
        self.client.force_login(self.role_user('COOK'))
        r=self.client.get(reverse('procurement:workflow'));self.assertEqual(r.status_code,200)
        urls={link['url'] for step in r.context['steps'] for link in step['links']}
        self.assertIn(reverse('meals:cooking_index'),urls)
        self.assertNotIn(reverse('procurement:workflow_headcounts'),urls)
        self.assertNotIn(reverse('procurement:workflow_preview'),urls)

    def test_supplier_keeps_separate_portal_and_cannot_use_internal_guide(self):
        self.client.force_login(self.role_user('SUPPLIER','SUPPLIER'))
        for name in ['procurement:workflow','procurement:workflow_headcounts','procurement:workflow_plans']:
            self.assertEqual(self.client.get(reverse(name)).status_code,403)
        self.assertEqual(self.client.get(reverse('procurement:portal_home')).status_code,200)

    def test_anonymous_cannot_open_guide(self):
        self.client.logout();self.assertEqual(self.client.get(reverse('procurement:workflow')).status_code,302)

    def test_progress_namespace_is_per_user_not_business_state(self):
        first=self.client.get(reverse('procurement:workflow')).context['progress_key']
        other=self.role_user('INVENTORY_MANAGER');self.client.force_login(other)
        second=self.client.get(reverse('procurement:workflow')).context['progress_key']
        self.assertNotEqual(first,second);self.assertNotIn(self.user.username,first)

    def test_native_details_and_faq_work_without_javascript(self):
        r=self.client.get(reverse('procurement:workflow'))
        self.assertContains(r,'data-guide-step',count=6)
        self.assertContains(r,'<noscript>')
        self.assertContains(r,'자주 묻는 질문')
        self.assertContains(r,'실측')

    def test_plan_list_post_never_confirms_orders(self):
        self.assertEqual(self.client.post(reverse('procurement:workflow_plans'),{}).status_code,405)
        self.assertEqual(ProcurementPlan.objects.count(),0)

    def test_every_rendered_step_link_is_authorized_and_connected(self):
        response=self.client.get(reverse('procurement:workflow'))
        for step in response.context['steps']:
            for link in step['links']:
                with self.subTest(url=link['url']):self.assertEqual(self.client.get(link['url']).status_code,200)

    def test_public_policy_signup_page_never_promises_immediate_access(self):
        from django.test import override_settings
        with override_settings(ACCOUNT_APPROVAL_MODE='auto',ACCOUNT_PUBLIC_SIGNUP_REQUIRES_APPROVAL=True):
            r=self.client.get(reverse('signup'))
            self.assertTrue('회원가입 후 바로 로그인' not in r.content.decode(), 'Approval-required signup must not promise immediate access; response omitted')
            self.assertContains(r,'계정 승인 후 로그인')

    def test_public_policy_both_signup_types_pending_existing_active_unchanged(self):
        from django.test import override_settings
        self.client.logout()
        with override_settings(ACCOUNT_APPROVAL_MODE='auto',ACCOUNT_PUBLIC_SIGNUP_REQUIRES_APPROVAL=True):
            for kind in ['DIETITIAN','SUPPLIER']:
                with self.subTest(kind=kind):
                    data={'username':'tutorial-new-'+kind.lower(),'email':kind.lower()+'@example.invalid','signup_type':kind,'password1':'Tutorial-Test-Only-Password-584!','password2':'Tutorial-Test-Only-Password-584!','company_name':'합성 업체','contact_name':'합성 담당','contact_phone':'000'}
                    self.assertRedirects(self.client.post(reverse('signup'),data),reverse('login'))
                    u=User.objects.get(username=data['username']);self.assertFalse(u.is_active);self.assertEqual(u.account_state,'PENDING')
                    self.assertFalse(u.is_superuser);self.assertFalse(self.client.login(username=u.username,password=data['password1']))
        self.user.refresh_from_db();self.assertTrue(self.user.is_active)

    def test_beginner_titles_and_one_continuous_educational_story(self):
        r=self.client.get(reverse('procurement:workflow'))
        expected=['어떤 음식을 만들까요?','몇 명이 먹을까요?','어떤 재료가 얼마나 필요할까요?',
                  '주문한 재료가 잘 도착했나요?','이제 음식을 준비해 볼까요?','오늘 급식은 어떻게 마무리할까요?']
        self.assertEqual([s['title'] for s in r.context['steps']],expected)
        for step in r.context['steps']:
            self.assertTrue(step['sentence'])
            self.assertTrue(step['example'])
            self.assertTrue(step['instructions'])
            self.assertIn('카레',step['example'])
        self.assertContains(r,'교육용 예시')
        self.assertContains(r,'실제 레시피나 영양 기준이 아닙니다')

    def test_beginner_guide_has_primary_action_and_optional_depth(self):
        r=self.client.get(reverse('procurement:workflow'))
        self.assertContains(r,'data-guide-more',count=6)
        self.assertContains(r,'data-guide-try',count=6)
        self.assertContains(r,'전체 6단계 보기')
        self.assertContains(r,'실제 업무 화면')
        self.assertNotContains(r,'/deliveries/')
        self.assertContains(r,'연습 데이터를 자동으로 만들지 않습니다')
        for step in r.context['steps']:
            self.assertIn(step['primary'],step['links'])

    def test_beginner_primary_links_are_filtered_for_limited_roles(self):
        for role in ('VIEWER','COOK'):
            self.client.force_login(self.role_user(role))
            steps=self.client.get(reverse('procurement:workflow')).context['steps']
            for step in steps:
                if step['primary']:
                    self.assertIn(step['primary'],step['links'])
                    self.assertEqual(self.client.get(step['primary']['url']).status_code,200)
                else:self.assertEqual(step['links'],[])

    def test_beginner_guidance_matches_real_button_labels(self):
        r=self.client.get(reverse('procurement:workflow'))
        for label in ('식수 저장','미리보기','발주예정서 저장','저장·확정'):
            self.assertContains(r,label)
        self.assertEqual(self.plan.headcount,120)
