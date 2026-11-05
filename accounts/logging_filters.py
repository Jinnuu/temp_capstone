import logging
import re
import traceback


class RecoveryRedactionFilter(logging.Filter):
    @staticmethod
    def redact(value):
        return re.sub(r"/accounts/recovery/[^\s\"'<>]*",'/accounts/recovery/[REDACTED]',value)

    def filter(self,record):
        record.msg=self.redact(record.getMessage())
        record.args=()
        request=getattr(record,"request",None)
        if request is not None and request.path.startswith("/accounts/recovery/"):
            record.request=None
        if record.exc_info:
            record.exc_text=self.redact(''.join(traceback.format_exception(*record.exc_info)))
            record.exc_info=None
        if record.stack_info:
            record.stack_info=self.redact(record.stack_info)
        return True
