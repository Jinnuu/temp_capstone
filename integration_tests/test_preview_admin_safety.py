"""Bootstrap and username transition contracts, synthetic accounts only."""
import io
from django.contrib.auth import get_user_model
from django.core.management import call_command, CommandError
from django.test import TestCase, override_settings
from accounts.models import AccessAudit

User = get_user_model()

class PreviewBootstrapSafetyTests(TestCase):
    def seed(self, admin='separate-test-admin-secret', demo='separate-test-demo-secret'):
        from accounts.preview_bootstrap import bootstrap_accounts
        secrets = {'preview_admin_password':admin, 'demo_password':demo}
        return bootstrap_accounts(lambda name: secrets[name])

    def test_admin_secret_is_separate(self):
        self.seed()
        admin=User.objects.get(username='admin');demo=User.objects.get(username='verify-nutritionist')
        self.assertTrue(admin.check_password('separate-test-admin-secret'))
        self.assertFalse(admin.check_password('separate-test-demo-secret'))
        self.assertTrue(demo.check_password('separate-test-demo-secret'))

    def test_missing_or_shared_admin_secret_fails_atomically(self):
        for secret in ['', 'separate-test-demo-secret']:
            with self.subTest(secret_configured=bool(secret)), self.assertRaises(CommandError):self.seed(admin=secret)
            self.assertEqual(User.objects.count(),0)

    def test_existing_renamed_main_is_preserved_without_password_reads(self):
        existing=User.objects.create_superuser('admin','admin@example.invalid','existing-test-only')
        from accounts.preview_bootstrap import bootstrap_accounts
        bootstrap_accounts(lambda name: 'test-demo-only' if name=='demo_password' else self.fail('must not read existing admin secret'))
        self.assertFalse(User.objects.filter(username='verify-admin').exists())
        self.assertEqual(User.objects.filter(is_superuser=True).count(),1)
        existing.refresh_from_db();self.assertTrue(existing.check_password('existing-test-only'))

    def test_non_admin_username_collision_fails_without_granting_privileges(self):
        existing=User.objects.create_user('admin')
        with self.assertRaises(CommandError):self.seed()
        existing.refresh_from_db();self.assertFalse(existing.is_superuser)
        self.assertFalse(User.objects.filter(username='verify-admin').exists())

    def test_repeated_seed_preserves_existing_password_and_accounts(self):
        self.seed();before=list(User.objects.order_by('pk').values_list('pk','username','password'))
        self.seed(admin='different-unused-admin',demo='different-unused-demo')
        self.assertEqual(before,list(User.objects.order_by('pk').values_list('pk','username','password')))

@override_settings(SNP_UI_PREVIEW=True)
class PreviewAdminRenameTests(TestCase):
    def setUp(self):
        self.admin=User.objects.create_superuser('verify-admin','owner@example.invalid','existing-password-only')

    def run_command(self, **kwargs):
        out=io.StringIO();call_command('rename_preview_admin',stdout=out,**kwargs);return out.getvalue()

    def test_default_is_dry_run_and_reports_no_password(self):
        output=self.run_command()
        self.admin.refresh_from_db();self.assertEqual(self.admin.username,'verify-admin')
        self.assertNotIn('existing-password-only',output)
        self.assertNotIn(self.admin.password,output)
        self.assertEqual(AccessAudit.objects.count(),0)

    def test_apply_requires_exact_pk(self):
        with self.assertRaises(CommandError):self.run_command(apply=True)
        self.admin.refresh_from_db();self.assertEqual(self.admin.username,'verify-admin')

    def test_apply_preserves_identity_credentials_privileges_and_audit(self):
        before={k:getattr(self.admin,k) for k in ['pk','password','email','is_staff','is_superuser','is_active','account_state']}
        self.run_command(apply=True,expected_pk=self.admin.pk)
        self.admin.refresh_from_db();self.assertEqual(self.admin.username,'admin')
        self.assertEqual(before,{k:getattr(self.admin,k) for k in before})
        self.assertEqual(User.objects.count(),1)
        self.assertTrue(AccessAudit.objects.filter(target=self.admin,action='account.username_changed').exists())

    def test_collision_never_merges_or_deletes(self):
        User.objects.create_user('admin')
        with self.assertRaises(CommandError):self.run_command(apply=True,expected_pk=self.admin.pk)
        self.assertEqual(User.objects.count(),2);self.assertTrue(User.objects.filter(username='verify-admin').exists())

    def test_repeat_apply_is_idempotent(self):
        self.run_command(apply=True,expected_pk=self.admin.pk)
        self.run_command(apply=True,expected_pk=self.admin.pk)
        self.assertEqual(AccessAudit.objects.filter(action='account.username_changed').count(),1)

    @override_settings(SNP_UI_PREVIEW=False)
    def test_non_preview_is_rejected(self):
        with self.assertRaises(CommandError):self.run_command()

    def test_rollback_by_same_pk_preserves_audit_foreign_key(self):
        self.run_command(apply=True,expected_pk=self.admin.pk)
        self.run_command(apply=True,expected_pk=self.admin.pk,source='admin',target='verify-admin')
        self.admin.refresh_from_db();self.assertEqual(self.admin.username,'verify-admin')
        self.assertEqual(AccessAudit.objects.filter(target=self.admin,action='account.username_changed').count(),2)

    def test_existing_foreign_keys_and_historical_labels_survive(self):
        from accounts.models import AdminRoleRequest, Announcement
        from procurement.models import PurchaseOrder
        from django.contrib.auth.models import Group
        group=Group.objects.create(name='unrelated-custom-group');self.admin.groups.add(group)
        request=AdminRoleRequest.objects.create(user=self.admin,reviewed_by=self.admin,reason='과거 신청',status='APPROVED')
        notice=Announcement.objects.create(author=self.admin,title='기존 공지',message='유지')
        order=PurchaseOrder.objects.create(supplier=self.admin,total_amount=100)
        previous=AccessAudit.objects.create(actor=self.admin,target=self.admin,actor_label='verify-admin',target_label='verify-admin',action='historical.event')
        self.run_command(apply=True,expected_pk=self.admin.pk)
        for row in [request,notice,order,previous]:row.refresh_from_db()
        self.assertEqual(request.user_id,self.admin.pk);self.assertEqual(request.reviewed_by_id,self.admin.pk)
        self.assertEqual(notice.author_id,self.admin.pk);self.assertEqual(order.supplier_id,self.admin.pk)
        self.assertEqual(previous.actor_id,self.admin.pk);self.assertEqual(previous.target_id,self.admin.pk)
        self.assertEqual(previous.target_label,'verify-admin')
        self.assertTrue(self.admin.groups.filter(pk=group.pk).exists())
