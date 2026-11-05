import json
import time
import logging
from django.core.management.base import BaseCommand
from accounts import recovery

logger=logging.getLogger('accounts.recovery')

class Command(BaseCommand):
    help='Deliver queued recovery email without exposing message contents.'
    requires_system_checks=[]

    def handle(self,*args,**options):
        while True:
            try:
                item=recovery.store().blpop(recovery.key('queue'),timeout=2)
                if item:
                    recovery.deliver_job(json.loads(item[1]))
            except Exception:
                logger.error('Recovery worker failed; no message details logged.')
                time.sleep(5)
