"""Real Redis atomic state + isolated Django DB/locmem receipt; no live accounts."""
import json
import re
import uuid
from concurrent.futures import ThreadPoolExecutor
from unittest.mock import patch
from django.test import TestCase,Client,override_settings
from django.contrib.auth import get_user_model
from django.contrib.auth.tokens import default_token_generator
from django.core import mail,signing
from django.urls import reverse
from django.utils.encoding import force_bytes
from django.utils.http import urlsafe_base64_encode
from accounts import recovery
from accounts.logging_filters import RecoveryRedactionFilter

PW='Test-Only-Account-Password-981!'
NEW='New-Test-Only-Password-473!'

class AccountRecoveryContracts(TestCase):
    def setUp(self):
        self.config=override_settings(ACCOUNT_RECOVERY_NAMESPACE='test:'+uuid.uuid4().hex,
            ACCOUNT_RECOVERY_DELIVERY_MODE='test',ACCOUNT_RECOVERY_ALLOW_TEST_DELIVERY=True,
            ACCOUNT_RECOVERY_BASE_URL='http://testserver',EMAIL_BACKEND='django.core.mail.backends.locmem.EmailBackend',
            DEFAULT_FROM_EMAIL='test@example.invalid',ACCOUNT_RECOVERY_EMAIL_LIMIT=3)
        self.config.enable();self.addCleanup(self.config.disable)
        recovery.store().ping()
        self.user=get_user_model().objects.create_user(username='approved-test',email='owner@example.invalid',name='테스트',password=PW,is_active=True)
        self.pending=get_user_model().objects.create_user(username='pending-test',email='pending@example.invalid',name='승인 대기',password=PW,is_active=False)
        mail.get_connection();mail.outbox=[]

    def deliver(self):
        raw=recovery.store().lpop(recovery.key('queue'))
        self.assertIsNotNone(raw)
        return recovery.deliver_job(json.loads(raw))

    def reset_url(self,user=None):
        u=user or self.user
        return reverse('password_reset_confirm',kwargs={'uidb64':urlsafe_base64_encode(force_bytes(u.pk)),'token':default_token_generator.make_token(u)})

    def test_active_login_logout_and_safe_next(self):
        response=self.client.post(reverse('login'),{'username':self.user.username,'password':PW,'next':'https://evil.invalid/'})
        self.assertRedirects(response,'/',fetch_redirect_response=False)
        self.assertIn('_auth_user_id',self.client.session)
        self.assertEqual(self.client.post(reverse('logout')).status_code,302)
        self.assertNotIn('_auth_user_id',self.client.session)

    def test_bad_password_does_not_reveal_approval(self):
        r=self.client.post(reverse('login'),{'username':self.pending.username,'password':'wrong'})
        self.assertEqual(r.status_code,200)
        self.assertNotContains(r,'관리자 승인 대기 중이거나 사용이 중지된 계정입니다.')
        self.assertNotIn('_auth_user_id',self.client.session)

    @override_settings(PASSWORD_HASHERS=['django.contrib.auth.hashers.MD5PasswordHasher','django.contrib.auth.hashers.PBKDF2PasswordHasher'])
    def test_correct_inactive_password_explains_approval_without_altering_user(self):
        from django.contrib.auth.hashers import make_password
        self.pending.password=make_password(PW,hasher="pbkdf2_sha256");self.pending.save(update_fields=["password"])
        before=self.pending.password
        r=self.client.post(reverse('login'),{'username':self.pending.username,'password':PW})
        self.assertContains(r,'관리자 승인 대기 중이거나 사용이 중지된 계정입니다.')
        self.pending.refresh_from_db();self.assertFalse(self.pending.is_active);self.assertEqual(self.pending.password,before)
        self.assertNotIn('_auth_user_id',self.client.session)

    def test_signup_requires_email_and_preserves_admin_approval(self):
        data={'username':'new-test','password1':PW,'password2':PW}
        self.assertEqual(self.client.post(reverse('signup'),data).status_code,200)
        self.assertFalse(get_user_model().objects.filter(username='new-test').exists())
        r=self.client.post(reverse('signup'),{**data,'email':'NEW@example.invalid','is_active':'1','role':'ADMIN'})
        self.assertEqual(r.status_code,302)
        u=get_user_model().objects.get(username='new-test');self.assertEqual(u.email,'new@example.invalid');self.assertFalse(u.is_active);self.assertEqual(u.role,'NUTRITIONIST')

    def test_registered_and_unknown_email_have_same_response_and_queue_path(self):
        for name in ['username_recovery','password_reset']:
            r1=self.client.post(reverse(name),{'email':self.user.email},follow=True)
            r2=self.client.post(reverse(name),{'email':'unknown@example.invalid'},follow=True)
            self.assertEqual(r1.status_code,r2.status_code);self.assertEqual(r1.content,r2.content)
        self.assertEqual(recovery.store().llen(recovery.key('queue')),4)
        self.assertEqual(mail.outbox,[])

    def test_username_email_receipt_requires_proof_before_display(self):
        self.client.post(reverse('username_recovery'),{'email':self.user.email})
        self.assertEqual(self.deliver(),'sent');self.assertEqual(len(mail.outbox),1)
        self.assertNotIn(self.user.username,mail.outbox[0].body)
        url=re.search(r'http://testserver(/accounts/recovery/\S+)',mail.outbox[0].body).group(1)
        entry=self.client.get(url);self.assertEqual(entry['Referrer-Policy'],'no-referrer')
        self.assertNotContains(self.client.get(entry.url),self.user.username)
        r=self.client.post(entry.url);self.assertContains(r,self.user.username);self.assertEqual(r['Referrer-Policy'],'same-origin');self.assertIn('no-store',r['Cache-Control'])
        self.client.get(url,follow=True)
        self.assertContains(self.client.post(reverse('username_recovery_confirm')),'만료되었거나 이미 사용한')

    def test_shared_email_lists_all_usernames_but_reset_excludes_inactive(self):
        get_user_model().objects.create_user(username='second-test',email=self.user.email,password=PW)
        self.pending.email=self.user.email;self.pending.save(update_fields=['email'])
        token=recovery.username_token(self.user.email)
        names=recovery.consume_username_token(token);self.assertEqual(set(names),{'approved-test','second-test','pending-test'})
        self.client.post(reverse('password_reset'),{'email':self.user.email});self.assertEqual(self.deliver(),'sent')
        self.assertEqual(len(mail.outbox),1);self.assertIn('approved-test',mail.outbox[0].body);self.assertIn('second-test',mail.outbox[0].body);self.assertNotIn('pending-test',mail.outbox[0].body)

    def test_identity_token_expiry_tampering_and_atomic_single_use(self):
        token=recovery.username_token(self.user.email)
        self.assertIsNone(recovery.consume_username_token(token+'bad'))
        with patch('django.core.signing.time.time',return_value=__import__('time').time()+1801):
            self.assertIsNone(recovery.consume_username_token(token))
        # Test the actual shared Redis GETDEL command across simultaneous clients.
        nonce='parallel-proof';key=recovery.key('proof:'+__import__('hashlib').sha256(nonce.encode()).hexdigest())
        recovery.store().set(key,'proof',ex=60)
        with ThreadPoolExecutor(max_workers=2) as executor:
            results=list(executor.map(lambda _:recovery.store().getdel(key),range(2)))
        self.assertEqual(results.count('proof'),1);self.assertEqual(results.count(None),1)

    def test_password_email_default_token_and_new_password_invalidate_sessions(self):
        old=Client();old.force_login(self.user)
        self.client.post(reverse('password_reset'),{'email':self.user.email});self.assertEqual(self.deliver(),'sent')
        url=re.search(r'http://testserver(/accounts/recovery/\S+)',mail.outbox[0].body).group(1)
        confirm=self.client.get(url).url
        self.assertEqual(self.client.post(confirm,{'new_password1':NEW,'new_password2':NEW}).status_code,302)
        self.user.refresh_from_db();self.assertTrue(self.user.check_password(NEW));self.assertTrue(self.user.is_active)
        self.assertNotContains(self.client.get(url,follow=True),'name="new_password1"')
        self.assertEqual(old.get('/').status_code,302)
        self.assertTrue(self.client.login(username=self.user.username,password=NEW))
        self.assertFalse(self.client.login(username=self.user.username,password=PW))

    def test_reset_token_expiry_invalid_token_and_weak_password(self):
        url=self.reset_url()
        with patch.object(default_token_generator,'_now',return_value=default_token_generator._now()+__import__('datetime').timedelta(seconds=1801)):
            self.assertNotContains(self.client.get(url),'name="new_password1"')
        self.assertNotContains(self.client.get(url[:-1]+'tampered/'),'name="new_password1"')
        confirm=self.client.get(url).url
        self.assertEqual(self.client.post(confirm,{'new_password1':'123','new_password2':'123'}).status_code,200)
        self.user.refresh_from_db();self.assertTrue(self.user.check_password(PW))

    def test_inactive_unusable_unknown_email_never_receive_reset(self):
        u=get_user_model().objects.create_user(username='no-password',email='sso@example.invalid');u.set_unusable_password();u.save()
        for email in [self.pending.email,u.email,'unknown@example.invalid']:
            self.client.post(reverse('password_reset'),{'email':email});self.assertEqual(self.deliver(),'no_eligible_account')
        self.assertEqual(mail.outbox,[])
        self.assertNotContains(self.client.get(self.reset_url(self.pending)),'name="new_password1"')

    def test_email_change_invalidates_reset_and_identity_proof(self):
        url=self.reset_url();token=recovery.username_token(self.user.email)
        self.user.email='changed@example.invalid';self.user.save(update_fields=['email'])
        self.assertNotContains(self.client.get(url),'name="new_password1"')
        self.assertEqual(recovery.consume_username_token(token),[])

    def test_rate_limits_shared_across_endpoints_and_unknown_addresses(self):
        for name in ['username_recovery','password_reset','username_recovery']:
            self.assertEqual(self.client.post(reverse(name),{'email':'unknown@example.invalid'}).status_code,302)
        self.assertEqual(self.client.post(reverse('password_reset'),{'email':'unknown@example.invalid'}).status_code,429)
        self.assertEqual(recovery.store().llen(recovery.key('queue')),3)

    def test_unconfigured_email_and_store_outage_are_not_success(self):
        with override_settings(ACCOUNT_RECOVERY_DELIVERY_MODE='disabled'):
            r=self.client.post(reverse('password_reset'),{'email':self.user.email});self.assertEqual(r.status_code,503);self.assertContains(r,'메일이 발송되지 않았습니다',status_code=503)
        with patch('accounts.recovery.store',side_effect=ConnectionError()):
            self.assertEqual(self.client.post(reverse('password_reset'),{'email':self.user.email}).status_code,503)

    def test_send_failure_logged_without_email_or_token(self):
        with patch('accounts.recovery.EmailMessage.send',side_effect=RuntimeError('sensitive transport text')):
            with self.assertLogs('accounts.recovery',level='ERROR') as captured:
                self.assertEqual(recovery.deliver_job({'kind':'username','email':self.user.email,'created':__import__('time').time()}),'delivery_failed')
        self.assertNotIn(self.user.email,' '.join(captured.output));self.assertNotIn('sensitive transport text',' '.join(captured.output))

    def test_csrf_enforced_on_requests_and_identity_confirmation(self):
        client=Client(enforce_csrf_checks=True)
        self.assertEqual(client.post(reverse('password_reset'),{'email':self.user.email}).status_code,403)
        token=recovery.username_token(self.user.email)
        self.assertEqual(client.post(reverse('username_confirm',args=[token])).status_code,403)
        client.get(reverse('password_reset'));csrf=client.cookies['csrftoken'].value
        self.assertEqual(client.post(reverse('password_reset'),{'email':self.user.email,'csrfmiddlewaretoken':csrf}).status_code,302)

    def test_recovery_pages_have_all_mode_controls_and_private_headers(self):
        for name in ['login','username_recovery','password_reset','password_reset_complete']:
            r=self.client.get(reverse(name));self.assertEqual(r.status_code,200)
            for mode in ['reference','green','civic']:self.assertContains(r,f'data-ui-mode="{mode}"')
        record=__import__('logging').LogRecord('test',30,'x',1,'Failure: %s',('/accounts/recovery/reset/uid/private-token/?x=1',),None)
        RecoveryRedactionFilter().filter(record);self.assertNotIn('private-token',record.getMessage())
