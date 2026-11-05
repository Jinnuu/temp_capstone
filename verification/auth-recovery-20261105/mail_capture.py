"""Ephemeral SMTP mailbox for synthetic tests. Never logs messages/URLs."""
import smtpd,asyncore,threading,json,email,email.policy
from http.server import HTTPServer,BaseHTTPRequestHandler
messages=[]
lock=threading.Lock()
class Capture(smtpd.SMTPServer):
    def process_message(self,peer,mailfrom,rcpttos,data,**kwargs):
        message=email.message_from_bytes(data,policy=email.policy.default)
        plain=message.get_body(preferencelist=('plain',))
        with lock:messages.append({'to':rcpttos,'body':plain.get_content() if plain else '', 'subject':str(message['Subject'])})
class Handler(BaseHTTPRequestHandler):
    def log_message(self,*args):pass
    def do_GET(self):
        with lock:body=json.dumps(messages).encode()
        self.send_response(200);self.send_header('Content-Type','application/json');self.end_headers();self.wfile.write(body)
Capture(('0.0.0.0',1025),None,decode_data=False)
threading.Thread(target=asyncore.loop,daemon=True).start()
HTTPServer(('0.0.0.0',8025),Handler).serve_forever()
