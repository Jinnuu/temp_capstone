"""Shared atomic limits, short-lived ownership proofs and asynchronous email jobs."""
import hashlib
import json
import logging
import secrets
import time
from urllib.parse import urlsplit
from django.conf import settings
from django.contrib.auth import get_user_model
from django.contrib.auth.forms import PasswordResetForm
from django.contrib.auth.tokens import default_token_generator
from django.core import signing
from django.core.mail import EmailMessage
from django.template.loader import render_to_string
from django.urls import reverse
from django.utils.crypto import salted_hmac
from django.utils.encoding import force_bytes
from django.utils.http import urlsafe_base64_encode

logger = logging.getLogger('accounts.recovery')
GENERIC_NOTICE = '요청을 접수했습니다. 등록된 이메일에 복구 가능한 계정이 있으면 안내 메일이 발송됩니다. 메일이 오지 않으면 스팸함을 확인하거나 관리자에게 문의해 주세요.'
UNAVAILABLE = '현재 이메일 복구 서비스를 사용할 수 없습니다. 메일이 발송되지 않았습니다. 관리자에게 문의해 주세요.'


def delivery_available():
    mode = getattr(settings, 'ACCOUNT_RECOVERY_DELIVERY_MODE', 'disabled')
    return (mode == 'smtp' and bool(settings.EMAIL_HOST) and bool(settings.DEFAULT_FROM_EMAIL) and (not settings.EMAIL_HOST_USER or bool(settings.EMAIL_HOST_PASSWORD))) or (mode == 'test' and getattr(settings, 'ACCOUNT_RECOVERY_ALLOW_TEST_DELIVERY', False))


def store():
    import redis
    return redis.Redis.from_url(settings.ACCOUNT_RECOVERY_REDIS_URL, decode_responses=True, socket_connect_timeout=2, socket_timeout=5)


def key(part):
    return getattr(settings, 'ACCOUNT_RECOVERY_NAMESPACE', 'snp:recovery') + ':' + part


def enqueue(kind, email, address):
    # User lookup and SMTP happen in a worker for both real and unknown addresses.
    client = store()
    hashed = lambda value: salted_hmac('snp-recovery-limit', value).hexdigest()
    allowed = client.eval('''
        for i=1,2 do
            if tonumber(redis.call('GET',KEYS[i]) or '0')>=tonumber(ARGV[i]) then return 0 end
        end
        for i=1,2 do
            local n=redis.call('INCR',KEYS[i])
            if n==1 then redis.call('EXPIRE',KEYS[i],ARGV[3]) end
        end
        return 1
    ''', 2, key('email:'+hashed(email)), key('source:'+hashed(address)),
        getattr(settings,'ACCOUNT_RECOVERY_EMAIL_LIMIT',3), getattr(settings,'ACCOUNT_RECOVERY_SOURCE_LIMIT',100), 3600)
    if not allowed:
        return False
    client.rpush(key('queue'), json.dumps({'kind':kind,'email':email,'created':time.time()}))
    return True


def username_token(email):
    nonce = secrets.token_urlsafe(32)
    ttl = getattr(settings,'ACCOUNT_RECOVERY_TIMEOUT',1800)
    store().set(key('proof:'+hashlib.sha256(nonce.encode()).hexdigest()), json.dumps({'email':email}), ex=ttl, nx=True)
    return signing.dumps(nonce, salt='snp-username-recovery')


def consume_username_token(token):
    try:
        nonce = signing.loads(token, salt='snp-username-recovery', max_age=getattr(settings,'ACCOUNT_RECOVERY_TIMEOUT',1800))
    except signing.BadSignature:
        return None
    raw = store().getdel(key('proof:'+hashlib.sha256(nonce.encode()).hexdigest()))
    if not raw:
        return None
    email = json.loads(raw)['email']
    return list(get_user_model().objects.filter(email__iexact=email).order_by('username').values_list('username', flat=True))


def recovery_url(path):
    base = settings.ACCOUNT_RECOVERY_BASE_URL.rstrip('/')
    parsed = urlsplit(base)
    if parsed.scheme not in ['http','https'] or not parsed.netloc or parsed.username or parsed.query or parsed.fragment:
        raise ValueError('Invalid recovery base URL')
    if parsed.scheme != 'https' and not getattr(settings,'ACCOUNT_RECOVERY_ALLOW_TEST_DELIVERY',False):
        raise ValueError('Public recovery links require HTTPS')
    return base + path


def deliver_job(job):
    """One message per request; no token, address or exception contents in logs."""
    if not delivery_available() or time.time()-job['created'] > 1800:
        return 'disabled_or_expired'
    email = job['email']
    context = {'expires_minutes':getattr(settings,'ACCOUNT_RECOVERY_TIMEOUT',1800)//60}
    if job['kind'] == 'username':
        if not get_user_model().objects.filter(email__iexact=email).exists():
            return 'no_eligible_account'
        token = username_token(email)
        context['url'] = recovery_url('/accounts'+reverse('username_confirm',urlconf='accounts.urls',args=[token]))
        template, subject = 'accounts/email/username.txt', '식수센스 아이디 확인 안내'
    elif job['kind'] == 'password':
        users = list(PasswordResetForm().get_users(email))
        if not users:
            return 'no_eligible_account'
        context['links'] = [{'username':u.username,'url':recovery_url('/accounts'+reverse('password_reset_confirm',urlconf='accounts.urls',kwargs={'uidb64':urlsafe_base64_encode(force_bytes(u.pk)),'token':default_token_generator.make_token(u)}))} for u in users]
        template, subject = 'accounts/email/password.txt', '식수센스 비밀번호 재설정 안내'
    else:
        return 'invalid_job'
    try:
        sent = EmailMessage(subject, render_to_string(template, context), settings.DEFAULT_FROM_EMAIL, [email]).send(fail_silently=False)
        if sent != 1:
            raise RuntimeError('delivery not accepted')
    except Exception:
        # SMTP exception strings may contain recipients or other sensitive information.
        logger.error('Recovery email delivery failed; verify mail transport configuration.')
        return 'delivery_failed'
    logger.info('Recovery email accepted by configured transport.')
    return 'sent'
