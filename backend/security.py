"""Session secrets never leave cookies; password KDF and evidence primitives."""
import base64
import hashlib
import hmac
import json
import secrets
from datetime import datetime, timezone

TERMS_VERSION = 'homologacao-2026-11-v1'
TERMS = ('Confirmo que revisei o PDF indicado por seu hash SHA-256 e desejo registrar minha intenção '
         'de assinar neste ambiente de homologação. O nome informado é autodeclarado; a posse do link '
         'não verifica minha identidade. Este teste não é assinatura ICP-Brasil e não foi homologado '
         'para uso jurídico. Nome declarado, versão dos termos, hashes e horários UTC serão '
         'armazenados como evidências de teste. Não envie dados pessoais ou contratos reais.')
TERMS_HASH = hashlib.sha256(TERMS.encode()).hexdigest()

def uid():
    return secrets.token_hex(16)

def token():
    return secrets.token_urlsafe(32)

def digest(data):
    return hashlib.sha256(data if isinstance(data, bytes) else data.encode()).hexdigest()

def canonical(data):
    return json.dumps(data, sort_keys=True, ensure_ascii=False, separators=(',', ':'), allow_nan=False)

def utc():
    return datetime.now(timezone.utc).isoformat(timespec='microseconds').replace('+00:00', 'Z')

def password_hash(password):
    salt = secrets.token_bytes(16)
    key = hashlib.scrypt(password.encode(), salt=salt, n=32768, r=8, p=1, maxmem=64*1024*1024)
    return base64.b64encode(salt+key).decode()

def password_ok(password, stored):
    try:
        raw = base64.b64decode(stored)
        key = hashlib.scrypt(password.encode(), salt=raw[:16], n=32768, r=8, p=1, maxmem=64*1024*1024)
        return hmac.compare_digest(key, raw[16:])
    except (ValueError, TypeError):
        return False

def event_hash(event):
    return digest(canonical({k: event[k] for k in ('id','org_id','envelope_id','event_type','actor','time_utc','payload','prev_event_hash')}))

def append_event(db, org, envelope, kind, actor, payload=None):
    prev = db.execute('SELECT event_hash FROM audit_events WHERE org_id=? ORDER BY seq DESC LIMIT 1', (org,)).fetchone()
    event = dict(id=uid(),org_id=org,envelope_id=envelope,event_type=kind,actor=actor,time_utc=utc(),payload=canonical(payload or {}),prev_event_hash=prev[0] if prev else '0'*64)
    event['event_hash'] = event_hash(event)
    db.execute('INSERT INTO audit_events(id,org_id,envelope_id,event_type,actor,time_utc,payload,prev_event_hash,event_hash) VALUES(:id,:org_id,:envelope_id,:event_type,:actor,:time_utc,:payload,:prev_event_hash,:event_hash)',event)
    return event

def verify_chain(events):
    prev = '0'*64
    for event in events:
        if event['prev_event_hash'] != prev or not hmac.compare_digest(event['event_hash'],event_hash(event)):
            return False
        prev = event['event_hash']
    return True


def verify_manifest(data,original=None,final=None):
    """Verifies internal commitments only; does not establish an external trust anchor."""
    try:
        if not verify_chain(data['events']):return False
        terms=data.get('terms',{})
        if terms and digest(terms['text'])!=terms['sha256']:return False
        eid=data.get('envelope_id')
        if eid:
            events=[e for e in data['events'] if e['envelope_id']==eid]
            uploaded=[json.loads(e['payload']).get('original_sha256') for e in events if e['event_type']=='DOCUMENT_UPLOADED']
            artifacts=[json.loads(e['payload']).get('final_sha256') for e in events if e['event_type']=='ARTIFACT_CREATED_TEST']
            if uploaded!=[data['original_sha256']]:return False
            if data.get('final_sha256') and artifacts!=[data['final_sha256']]:return False
            for consent in data.get('consents',[]):
                if digest(consent['terms_text'])!=consent['terms_sha256']:return False
                if not any(e['event_type']=='CONSENT_ACCEPTED' and e['actor']==consent['signer_id'] and json.loads(e['payload']).get('terms_sha256')==consent['terms_sha256'] for e in events):return False
            for signer in data.get('signers',[]):
                if signer['status']=='CONFIRMED_TEST' and not any(e['event_type']=='INTENT_CONFIRMED_TEST' and e['actor']==signer['id'] and json.loads(e['payload']).get('declared_name_sha256')==digest(signer['declared_name']) for e in events):return False
        if original is not None and digest(original)!=data['original_sha256']:return False
        if final is not None and digest(final)!=data['final_sha256']:return False
        return True
    except (KeyError,ValueError,TypeError):
        return False
