"""Pure HMAC envelope helper only. No registration, queue or network delivery yet."""
import hashlib
import hmac
import time

def sign(secret:bytes,event_id:str,timestamp:int,body:bytes):
    message=f'{event_id}.{timestamp}.'.encode()+body
    return 'v1='+hmac.new(secret,message,hashlib.sha256).hexdigest()

def verify(secret:bytes,event_id:str,timestamp:int,body:bytes,signature:str,now=None):
    if abs((time.time() if now is None else now)-timestamp)>300:return False
    return hmac.compare_digest(sign(secret,event_id,timestamp,body),signature)
