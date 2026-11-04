"""Assina Brasil: runnable, local-only homologation API and frontend."""
import io
import json
import os
import re
import sqlite3
import time
from pathlib import Path
from urllib.parse import urlsplit
from fastapi import FastAPI, HTTPException, Request, Response, UploadFile, File, Form
from fastapi.exceptions import RequestValidationError
from fastapi.responses import JSONResponse, FileResponse, HTMLResponse
from starlette.middleware.trustedhost import TrustedHostMiddleware
from .db import Database
from .config import resolve_origin,HEALTHCHECK_HOST
from .storage import Store, validate_pdf, MAX_PDF
from .security import (uid,token,digest,canonical,utc,password_hash,password_ok,append_event,verify_chain,
                       TERMS,TERMS_VERSION,TERMS_HASH)
from .models import (Credentials,Register,OrgInput,Brand,SignerInput,TokenInput,ConsentInput,ConfirmInput,
                     TemplateInput,MemberInput,PasswordChange)
from .evidence import final_pdf
from .fonts import styles_with_fonts

BASE=Path(__file__).resolve().parent.parent
SESSION_SECONDS=8*3600

class BodyLimit:
    def __init__(self,app): self.app=app
    async def __call__(self,scope,receive,send):
        if scope['type']!='http' or scope['method'] in ('GET','HEAD'):
            return await self.app(scope,receive,send)
        chunks=[];total=0
        while True:
            msg=await receive()
            if msg['type']=='http.disconnect': return
            chunk=msg.get('body',b'');total+=len(chunk)
            if total>MAX_PDF+128*1024:
                return await JSONResponse({'detail':'Requisição excede o limite.'},413)(scope,receive,send)
            chunks.append(chunk)
            if not msg.get('more_body',False): break
        done=False
        async def replay():
            nonlocal done
            if not done:
                done=True;return {'type':'http.request','body':b''.join(chunks),'more_body':False}
            return await receive()
        return await self.app(scope,replay,send)

def create_app(data_dir=None,origin=None):
    if os.getenv('ASSINA_MODE','homologacao')!='homologacao':
        raise RuntimeError('Produção bloqueada: versão exclusiva de homologação.')
    data=Path(data_dir or os.getenv('ASSINA_DATA',BASE/'runtime'))
    expected_origin,parsed=resolve_origin(origin)
    db=Database(data/'assina.sqlite3');store=Store(data/'objects')
    dummy_hash=password_hash('senha-inexistente-de-teste-2026')
    app=FastAPI(title='Assina Brasil - Homologação',version='0.2.0',docs_url=None,redoc_url=None,openapi_url='/api/openapi.json')
    app.state.db=db;app.state.store=store;app.state.origin=expected_origin
    app.add_middleware(TrustedHostMiddleware,allowed_hosts=[parsed.hostname,HEALTHCHECK_HOST])
    app.add_middleware(BodyLimit)

    def fail(status,msg): raise HTTPException(status,msg)

    def limited(key,limit=100,seconds=60):
        now=time.time()
        with db.tx() as c:
            row=c.execute('SELECT * FROM rate_limits WHERE bucket=?',(key,)).fetchone()
            if not row or now-row['starts']>=seconds:
                c.execute('INSERT OR REPLACE INTO rate_limits VALUES(?,?,1)',(key,now));return
            if row['hits']>=limit: fail(429,'Muitas tentativas. Aguarde antes de tentar novamente.')
            c.execute('UPDATE rate_limits SET hits=hits+1 WHERE bucket=?',(key,))

    @app.middleware('http')
    async def guards(request,call_next):
        path=request.url.path
        host=request.headers.get('host','').split(':',1)[0].lower()
        if host==HEALTHCHECK_HOST and (path!='/api/health' or request.method!='GET'):
            response=JSONResponse({'detail':'Host reservado para healthcheck.'},400)
        elif path=='/api/health' and request.method=='GET':
            # Deployment probes never consume the users' rate-limit bucket.
            response=await call_next(request)
        elif path.startswith('/api/'):
            ip=request.client.host if request.client else 'unknown'
            # Rate key uses a keyed digest, not a stored raw IP; forwarded headers untrusted.
            import hmac,hashlib
            key=hmac.new(store.rate_key,ip.encode(),hashlib.sha256).hexdigest()
            group='auth' if path.startswith('/api/auth/') else 'public' if path.startswith('/api/signing/') else 'api'
            try:
                limited(group+key, 20 if group=='auth' else 100,60)
                if request.method not in ('GET','HEAD','OPTIONS'):
                    if request.headers.get('origin')!=expected_origin:
                        fail(403,'Origem da requisição não permitida.')
                    if not path.endswith('/envelopes') and 'application/json' not in request.headers.get('content-type',''):
                        fail(415,'Envie conteúdo JSON.')
            except HTTPException as exc:
                response=JSONResponse({'detail':exc.detail},exc.status_code)
            else:
                response=await call_next(request)
        else: response=await call_next(request)
        response.headers.update({
            'X-Content-Type-Options':'nosniff','Referrer-Policy':'no-referrer',
            'X-Frame-Options':'SAMEORIGIN','Cache-Control':'no-store',
            'Permissions-Policy':'camera=(), microphone=(), geolocation=()',
            'Content-Security-Policy':"default-src 'self'; script-src 'self'; style-src 'self'; img-src 'self' data:; connect-src 'self'; frame-src 'self' blob:; object-src 'none'; base-uri 'none'; form-action 'self'; frame-ancestors 'self'"
        })
        if parsed.scheme=='https':response.headers['Strict-Transport-Security']='max-age=31536000'
        return response

    @app.exception_handler(RequestValidationError)
    async def validation_error(request,exc):
        # Do not echo supplied password, token, PDF or other PII in validation errors.
        return JSONResponse({'detail':'Confira os campos obrigatórios e os limites informados.'},422)

    def user(c,request):
        raw=request.cookies.get('assina_session','')
        row=c.execute('SELECT u.*,s.csrf FROM sessions s JOIN users u ON u.id=s.user_id WHERE s.token_hash=? AND s.expires_at>?',(digest(raw),time.time())).fetchone()
        if not row: fail(401,'Entre na sua conta para continuar.')
        if request.method not in ('GET','HEAD'):
            import hmac
            if not hmac.compare_digest(request.headers.get('x-csrf-token',''),row['csrf']):fail(403,'Sessão de formulário inválida. Recarregue a página.')
        return row

    def access(c,request,write=False,admin=False):
        u=user(c,request);org=request.headers.get('x-organization','')
        member=c.execute('SELECT role FROM memberships WHERE user_id=? AND org_id=?',(u['id'],org)).fetchone()
        if not member: fail(404,'Empresa não encontrada.')
        if admin and member['role'] not in ('owner','admin'):fail(403,'Esta ação exige administração da empresa.')
        if write and member['role']=='viewer':fail(403,'Seu acesso é apenas de leitura.')
        return u,org,member['role']

    def envelope(c,id,org):
        e=c.execute('SELECT * FROM envelopes WHERE id=? AND org_id=?',(id,org)).fetchone()
        if not e: fail(404,'Documento não encontrado.')
        return e

    def signing(c,raw):
        row=c.execute('SELECT t.*,s.envelope_id,s.name,s.position,s.status AS signer_status FROM signing_sessions t JOIN signers s ON s.id=t.signer_id AND s.org_id=t.org_id WHERE t.token_hash=?',(digest(raw),)).fetchone()
        if not row or row['revoked_at'] or row['consumed_at'] or row['expires_at']<=time.time():fail(404,'Link indisponível ou expirado.')
        e=envelope(c,row['envelope_id'],row['org_id'])
        if e['status'] not in ('SENT','IN_PROGRESS') or e['expires_at']<=time.time():fail(404,'Link indisponível ou expirado.')
        if e['ordered'] and c.execute('SELECT 1 FROM signers WHERE envelope_id=? AND position<? AND status!=?',(e['id'],row['position'],'CONFIRMED_TEST')).fetchone():fail(409,'Aguarde a confirmação dos participantes anteriores.')
        return row,e

    def cookie(response,raw):
        response.set_cookie('assina_session',raw,httponly=True,secure=parsed.scheme=='https',samesite='strict',max_age=SESSION_SECONDS,path='/')

    def start_session(c,uid_,response):
        raw=token();csrf=token()
        c.execute('INSERT INTO sessions VALUES(?,?,?,?)',(digest(raw),uid_,csrf,time.time()+SESSION_SECONDS))
        cookie(response,raw)
        return {'csrf':csrf,'mode':'homologacao'}

    @app.get('/api/docs',response_class=HTMLResponse)
    def api_reference():
        from html import escape
        spec=app.openapi()
        rows=''.join('<tr><td>'+escape(method.upper())+'</td><td><code>'+escape(path)+'</code></td><td>'+escape(op.get('summary',''))+'</td></tr>' for path,methods in spec['paths'].items() for method,op in methods.items() if method in ('get','post','patch','delete'))
        return '<!doctype html><html lang="pt-BR"><head><meta charset="utf-8"><meta name="viewport" content="width=device-width,initial-scale=1"><link rel="stylesheet" href="/assets/style.css"><title>API - Assina Brasil</title></head><body><main class="signin-shell"><h1>Referência da API de homologação</h1><p>API da mesma origem. Sessão HttpOnly e headers X-CSRF-Token / X-Organization. Rotas signing usam token de acesso específico no corpo JSON. Documentação de consulta, sem executar ações.</p><p><a href="/api/openapi.json">Abrir OpenAPI JSON</a> · <a href="/app">Voltar ao aplicativo</a></p><div class="tablewrap"><table class="table"><thead><tr><th>Método</th><th>Rota</th><th>Descrição</th></tr></thead><tbody>'+rows+'</tbody></table></div></main></body></html>'

    @app.get('/api/health')
    def health():return {'status':'ok','mode':'homologacao','production_ready':False,'icp_brasil_enabled':False}

    @app.post('/api/auth/register',status_code=201)
    def register(body:Register,response:Response):
        hashed=password_hash(body.password)
        with db.tx() as c:
            if c.execute('SELECT 1 FROM users WHERE email=?',(body.email,)).fetchone():fail(409,'Não foi possível criar a conta com estes dados.')
            u=uid();o=uid();now=utc()
            c.execute('INSERT INTO users VALUES(?,?,?,?,?)',(u,body.email,body.name,hashed,now))
            c.execute('INSERT INTO organizations(id,name,brand_name,created_at) VALUES(?,?,?,?)',(o,body.organization,'Assina Brasil',now))
            c.execute('INSERT INTO memberships VALUES(?,?,?)',(o,u,'owner'))
            append_event(c,o,None,'ORGANIZATION_CREATED',u)
            return start_session(c,u,response)

    @app.post('/api/auth/login')
    def login(body:Credentials,response:Response):
        with db.tx() as c:
            u=c.execute('SELECT * FROM users WHERE email=?',(body.email,)).fetchone()
            valid=password_ok(body.password,u['password_hash'] if u else dummy_hash)
            if not u or not valid:fail(401,'E-mail ou senha inválidos.')
            return start_session(c,u['id'],response)

    @app.get('/api/me')
    def me(request:Request):
        with db.tx() as c:
            u=user(c,request)
            orgs=[dict(o) for o in c.execute('SELECT o.*,m.role FROM organizations o JOIN memberships m ON m.org_id=o.id WHERE m.user_id=? ORDER BY o.created_at',(u['id'],))]
            return {'user':{'id':u['id'],'name':u['name'],'email':u['email']},'organizations':orgs,'csrf':u['csrf'],'mode':'homologacao'}

    @app.post('/api/auth/logout')
    def logout(request:Request,response:Response):
        with db.tx() as c:
            user(c,request);c.execute('DELETE FROM sessions WHERE token_hash=?',(digest(request.cookies.get('assina_session','')),))
        response.delete_cookie('assina_session');return {'ok':True}

    @app.post('/api/auth/password')
    def change_password(body:PasswordChange,request:Request,response:Response):
        with db.tx() as c:
            u=user(c,request)
            if not password_ok(body.current_password,u['password_hash']):fail(401,'Senha atual inválida.')
            c.execute('UPDATE users SET password_hash=? WHERE id=?',(password_hash(body.new_password),u['id']))
            c.execute('DELETE FROM sessions WHERE user_id=?',(u['id'],))
        response.delete_cookie('assina_session');return {'ok':True,'message':'Senha atualizada. Entre novamente.'}

    @app.post('/api/auth/recover')
    def recover():fail(503,'Recuperação por e-mail ainda não configurada. Consulte o administrador da homologação.')

    @app.post('/api/organizations',status_code=201)
    def create_org(body:OrgInput,request:Request):
        with db.tx() as c:
            u=user(c,request);o=uid()
            c.execute('INSERT INTO organizations(id,name,brand_name,created_at) VALUES(?,?,?,?)',(o,body.name,'Assina Brasil',utc()))
            c.execute('INSERT INTO memberships VALUES(?,?,?)',(o,u['id'],'owner'))
            append_event(c,o,None,'ORGANIZATION_CREATED',u['id'])
            return {'id':o}

    @app.patch('/api/organization')
    def brand(body:Brand,request:Request):
        with db.tx() as c:
            u,o,_=access(c,request,admin=True)
            c.execute('UPDATE organizations SET brand_name=?,color=? WHERE id=?',(body.brand_name,body.color,o))
            append_event(c,o,None,'BRAND_UPDATED',u['id'])
        return {'ok':True}

    @app.get('/api/members')
    def members(request:Request):
        with db.tx() as c:
            _,o,_=access(c,request,admin=True)
            return [dict(r) for r in c.execute('SELECT u.name,u.email,m.role FROM memberships m JOIN users u ON u.id=m.user_id WHERE m.org_id=?',(o,))]

    @app.post('/api/members')
    def add_member(body:MemberInput,request:Request):
        with db.tx() as c:
            u,o,role=access(c,request,admin=True)
            if body.role=='admin' and role!='owner':fail(403,'Somente o proprietário pode atribuir administração.')
            target=c.execute('SELECT id FROM users WHERE email=?',(body.email,)).fetchone()
            if not target:fail(422,'A conta precisa estar previamente cadastrada neste ambiente.')
            old=c.execute('SELECT role FROM memberships WHERE org_id=? AND user_id=?',(o,target['id'])).fetchone()
            if target['id']==u['id'] or old and old['role'] in ('owner','admin') and role!='owner':fail(403,'Alteração de permissão não permitida.')
            if old and old['role']=='owner':fail(403,'Não é possível alterar o proprietário por este fluxo.')
            c.execute('INSERT INTO memberships VALUES(?,?,?) ON CONFLICT(org_id,user_id) DO UPDATE SET role=excluded.role',(o,target['id'],body.role))
            append_event(c,o,None,'MEMBER_UPDATED',u['id'],{'user_id':target['id'],'role':body.role})
        return {'ok':True,'email_sent':False}

    @app.get('/api/envelopes')
    def envelopes(request:Request):
        with db.tx() as c:
            _,o,_=access(c,request)
            rows=c.execute('SELECT e.*,COUNT(s.id) AS signer_count,COALESCE(SUM(s.status="CONFIRMED_TEST"),0) AS confirmed_count FROM envelopes e LEFT JOIN signers s ON s.envelope_id=e.id AND s.org_id=e.org_id WHERE e.org_id=? GROUP BY e.id ORDER BY e.created_at DESC',(o,))
            return [{k:r[k] for k in r.keys() if k!='original_key'} for r in rows]

    @app.post('/api/envelopes',status_code=201)
    async def create_envelope(request:Request,file:UploadFile=File(...),title:str=Form(...),ordered:bool=Form(False),days:int=Form(7),test_only:bool=Form(False)):
        if not test_only:fail(422,'Confirme o uso exclusivo de documento fictício de homologação.')
        if not 2<=len(title.strip())<=150 or not 1<=days<=30:fail(422,'Título ou prazo inválido.')
        if file.content_type!='application/pdf':fail(422,'O arquivo deve ter tipo application/pdf.')
        # Authorize before parsing untrusted PDFs.
        with db.tx() as c:access(c,request,write=True)
        raw=await file.read(MAX_PDF+1);pages=validate_pdf(raw);key=None
        try:
            with db.tx() as c:
                u,o,_=access(c,request,write=True)
                # Local test quota; commercial billing is not connected.
                count=c.execute('SELECT COUNT(*) FROM envelopes WHERE org_id=?',(o,)).fetchone()[0]
                if count>=100:fail(409,'Limite de 100 envelopes de homologação atingido.')
                eid=uid();key=store.put(o,raw)
                c.execute('INSERT INTO envelopes VALUES(?,?,?,?,?,?,?,?,?,?,?)',(eid,o,title.strip(),'DRAFT',digest(raw),key,len(raw),pages,int(ordered),utc(),time.time()+days*86400))
                append_event(c,o,eid,'DOCUMENT_UPLOADED',u['id'],{'original_sha256':digest(raw),'size':len(raw),'pages':pages})
                return {'id':eid,'original_sha256':digest(raw)}
        except BaseException:
            if key:store.remove(key)
            raise

    @app.get('/api/envelopes/{eid}')
    def detail(eid:str,request:Request):
        with db.tx() as c:
            _,o,_=access(c,request);e=dict(envelope(c,eid,o));e.pop('original_key')
            e['signers']=[dict(r) for r in c.execute('SELECT * FROM signers WHERE org_id=? AND envelope_id=? ORDER BY position',(o,eid))]
            e['events']=[dict(r) for r in c.execute('SELECT * FROM audit_events WHERE org_id=? AND envelope_id=? ORDER BY seq',(o,eid))]
            a=c.execute('SELECT sha256,created_at FROM artifacts WHERE org_id=? AND envelope_id=?',(o,eid)).fetchone()
            e['artifact']=dict(a) if a else None
            return e

    @app.post('/api/envelopes/{eid}/signers',status_code=201)
    def add_signer(eid:str,body:SignerInput,request:Request):
        with db.tx() as c:
            u,o,_=access(c,request,write=True);e=envelope(c,eid,o)
            if e['status']!='DRAFT':fail(409,'Participantes só podem ser alterados no rascunho.')
            count=c.execute('SELECT COUNT(*) FROM signers WHERE envelope_id=?',(eid,)).fetchone()[0]
            if count>=20:fail(422,'Limite de 20 participantes por envelope.')
            if c.execute('SELECT 1 FROM signers WHERE envelope_id=? AND email=?',(eid,body.email)).fetchone():fail(409,'Este e-mail já participa do envelope.')
            position=c.execute('SELECT COALESCE(MAX(position),0)+1 FROM signers WHERE envelope_id=?',(eid,)).fetchone()[0]
            sid=uid();c.execute('INSERT INTO signers(id,org_id,envelope_id,name,email,position) VALUES(?,?,?,?,?,?)',(sid,o,eid,body.name,body.email,position))
            append_event(c,o,eid,'SIGNER_ADDED',u['id'],{'signer_id':sid,'position':position})
            return {'id':sid}

    @app.delete('/api/envelopes/{eid}/signers/{sid}')
    def remove_signer(eid:str,sid:str,request:Request):
        with db.tx() as c:
            u,o,_=access(c,request,write=True);e=envelope(c,eid,o)
            if e['status']!='DRAFT':fail(409,'Participantes só podem ser alterados no rascunho.')
            c.execute('DELETE FROM signers WHERE id=? AND org_id=? AND envelope_id=?',(sid,o,eid))
            append_event(c,o,eid,'SIGNER_REMOVED',u['id'],{'signer_id':sid})
        return {'ok':True}

    @app.post('/api/envelopes/{eid}/send')
    def send(eid:str,request:Request):
        with db.tx() as c:
            u,o,_=access(c,request,write=True);e=envelope(c,eid,o)
            if e['status']!='DRAFT' or e['expires_at']<=time.time():fail(409,'Envelope não pode ser disponibilizado.')
            if not c.execute('SELECT 1 FROM signers WHERE envelope_id=?',(eid,)).fetchone():fail(422,'Adicione pelo menos um participante.')
            store.get(e['original_key'],e['original_sha256'])
            c.execute('UPDATE envelopes SET status="SENT" WHERE id=?',(eid,))
            append_event(c,o,eid,'ENVELOPE_AVAILABLE_TEST',u['id'],{'email_sent':False})
        return {'ok':True,'email_sent':False}

    @app.post('/api/envelopes/{eid}/links/{sid}')
    def issue(eid:str,sid:str,request:Request):
        with db.tx() as c:
            u,o,_=access(c,request,write=True);e=envelope(c,eid,o)
            s=c.execute('SELECT * FROM signers WHERE id=? AND envelope_id=? AND org_id=?',(sid,eid,o)).fetchone()
            if not s or s['status']!='PENDING' or e['status'] not in ('SENT','IN_PROGRESS') or e['expires_at']<=time.time():fail(409,'Não é possível emitir este link.')
            now=utc();raw=token();expires=min(time.time()+86400,e['expires_at'])
            c.execute('UPDATE signing_sessions SET revoked_at=? WHERE signer_id=? AND revoked_at IS NULL AND consumed_at IS NULL',(now,sid))
            c.execute('INSERT INTO signing_sessions(token_hash,org_id,signer_id,expires_at) VALUES(?,?,?,?)',(digest(raw),o,sid,expires))
            append_event(c,o,eid,'LINK_ISSUED',u['id'],{'signer_id':sid,'expires_at':expires})
            return {'url':expected_origin+'/assinar#'+raw,'expires_at':expires,'email_sent':False}

    @app.post('/api/envelopes/{eid}/revoke/{sid}')
    def revoke(eid:str,sid:str,request:Request):
        with db.tx() as c:
            u,o,_=access(c,request,write=True);envelope(c,eid,o)
            if not c.execute('SELECT 1 FROM signers WHERE id=? AND envelope_id=? AND org_id=?',(sid,eid,o)).fetchone():fail(404,'Participante não encontrado.')
            c.execute('UPDATE signing_sessions SET revoked_at=? WHERE signer_id=? AND org_id=? AND consumed_at IS NULL',(utc(),sid,o))
            append_event(c,o,eid,'LINK_REVOKED',u['id'],{'signer_id':sid})
        return {'ok':True}

    @app.post('/api/envelopes/{eid}/cancel')
    def cancel(eid:str,request:Request):
        with db.tx() as c:
            u,o,_=access(c,request,write=True);e=envelope(c,eid,o)
            if e['status'] in ('CANCELED','COMPLETED_TEST'):fail(409,'Envelope já encerrado.')
            c.execute('UPDATE envelopes SET status="CANCELED" WHERE id=?',(eid,))
            c.execute('UPDATE signing_sessions SET revoked_at=? WHERE signer_id IN (SELECT id FROM signers WHERE envelope_id=?) AND consumed_at IS NULL',(utc(),eid))
            append_event(c,o,eid,'ENVELOPE_CANCELED',u['id'])
        return {'ok':True}

    @app.get('/api/envelopes/{eid}/pdf')
    def original(eid:str,request:Request):
        with db.tx() as c:
            _,o,_=access(c,request);e=envelope(c,eid,o)
            raw=store.get(e['original_key'],e['original_sha256'])
        return Response(raw,media_type='application/pdf',headers={'Content-Disposition':'attachment; filename="original-teste.pdf"'})

    @app.get('/api/envelopes/{eid}/artifact')
    def artifact(eid:str,request:Request):
        with db.tx() as c:
            _,o,_=access(c,request);envelope(c,eid,o)
            a=c.execute('SELECT * FROM artifacts WHERE envelope_id=? AND org_id=?',(eid,o)).fetchone()
            if not a:fail(404,'Artefato de homologação ainda não disponível.')
            raw=store.get(a['storage_key'],a['sha256'])
        return Response(raw,media_type='application/pdf',headers={'Content-Disposition':'attachment; filename="homologacao-sem-icp.pdf"'})

    def evidence_payload(c,o,eid=None):
        events=[dict(r) for r in c.execute('SELECT * FROM audit_events WHERE org_id=? ORDER BY seq',(o,))]
        result={'mode':'homologacao','identity_verified':False,'trusted_timestamp':False,'worm_storage':False,
                'chain_scope':'organization','chain_valid':verify_chain(events),'events':events,
                'terms':{'version':TERMS_VERSION,'text':TERMS,'sha256':TERMS_HASH}}
        if eid:
            e=envelope(c,eid,o);store.get(e['original_key'],e['original_sha256'])
            a=c.execute('SELECT * FROM artifacts WHERE org_id=? AND envelope_id=?',(o,eid)).fetchone()
            if a:store.get(a['storage_key'],a['sha256'])
            result.update({'envelope_id':eid,'original_sha256':e['original_sha256'],'final_sha256':a['sha256'] if a else None,
                           'signers':[dict(r) for r in c.execute('SELECT id,position,declared_name,confirmed_at,status FROM signers WHERE org_id=? AND envelope_id=? ORDER BY position',(o,eid))],
                           'consents':[dict(r) for r in c.execute('SELECT signer_id,terms_version,terms_sha256,terms_text,accepted_at FROM consents WHERE org_id=? AND signer_id IN (SELECT id FROM signers WHERE envelope_id=?)',(o,eid))]})
        return result

    @app.get('/api/envelopes/{eid}/evidence')
    def evidence(eid:str,request:Request):
        with db.tx() as c:
            _,o,_=access(c,request);return evidence_payload(c,o,eid)

    @app.get('/api/audit')
    def audit(request:Request):
        with db.tx() as c:
            _,o,_=access(c,request);return evidence_payload(c,o)

    @app.post('/api/signing/open')
    def open_link(body:TokenInput):
        with db.tx() as c:
            s,e=signing(c,body.token);store.get(e['original_key'],e['original_sha256'])
            append_event(c,s['org_id'],e['id'],'LINK_OPENED',s['signer_id'])
            org=c.execute('SELECT brand_name,color FROM organizations WHERE id=?',(s['org_id'],)).fetchone()
            return {'title':e['title'],'signer_name':s['name'],'original_sha256':e['original_sha256'],'pages':e['pages'],
                    'terms':TERMS,'terms_version':TERMS_VERSION,'brand':dict(org),'identity_verified':False}

    @app.post('/api/signing/pdf')
    def signing_pdf(body:TokenInput):
        with db.tx() as c:
            s,e=signing(c,body.token);raw=store.get(e['original_key'],e['original_sha256'])
            append_event(c,s['org_id'],e['id'],'DOCUMENT_FETCHED',s['signer_id'])
        return Response(raw,media_type='application/pdf')

    @app.post('/api/signing/consent')
    def consent(body:ConsentInput):
        if not body.accepted or body.terms_version!=TERMS_VERSION:fail(422,'Aceite os termos atuais para continuar.')
        with db.tx() as c:
            s,e=signing(c,body.token)
            old=c.execute('SELECT terms_sha256 FROM consents WHERE token_hash=?',(digest(body.token),)).fetchone()
            if old and old[0]!=TERMS_HASH:fail(409,'Os termos mudaram. Solicite um novo link antes de continuar.')
            if not c.execute('SELECT 1 FROM consents WHERE token_hash=?',(digest(body.token),)).fetchone():
                c.execute('INSERT INTO consents VALUES(?,?,?,?,?,?,?,?)',(uid(),s['org_id'],s['signer_id'],digest(body.token),TERMS_VERSION,TERMS_HASH,TERMS,utc()))
                append_event(c,s['org_id'],e['id'],'CONSENT_ACCEPTED',s['signer_id'],{'terms_version':TERMS_VERSION,'terms_sha256':TERMS_HASH})
        return {'ok':True}

    @app.post('/api/signing/confirm')
    def confirm(body:ConfirmInput):
        artifact_key=None
        try:
            with db.tx() as c:
                s,e=signing(c,body.token)
                if body.original_sha256!=e['original_sha256']:fail(409,'O hash do documento não corresponde ao documento revisado.')
                if not c.execute('SELECT 1 FROM consents WHERE token_hash=? AND terms_version=? AND terms_sha256=?',(digest(body.token),TERMS_VERSION,TERMS_HASH)).fetchone():fail(422,'Consentimento atual obrigatório.')
                original=store.get(e['original_key'],e['original_sha256']);now=utc()
                c.execute('UPDATE signing_sessions SET consumed_at=? WHERE token_hash=? AND consumed_at IS NULL',(now,digest(body.token)))
                c.execute('UPDATE signers SET status="CONFIRMED_TEST",confirmed_at=?,declared_name=? WHERE id=?',(now,body.declared_name,s['signer_id']))
                append_event(c,s['org_id'],e['id'],'INTENT_CONFIRMED_TEST',s['signer_id'],{'original_sha256':e['original_sha256'],'declared_name_sha256':digest(body.declared_name),'identity_verified':False})
                pending=c.execute('SELECT 1 FROM signers WHERE envelope_id=? AND status="PENDING"',(e['id'],)).fetchone()
                if pending:
                    c.execute('UPDATE envelopes SET status="IN_PROGRESS" WHERE id=?',(e['id'],))
                else:
                    c.execute('UPDATE envelopes SET status="COMPLETED_TEST" WHERE id=?',(e['id'],))
                    event=append_event(c,s['org_id'],e['id'],'ENVELOPE_COMPLETED_TEST',s['signer_id'])
                    signers=[dict(r) for r in c.execute('SELECT * FROM signers WHERE envelope_id=? ORDER BY position',(e['id'],))]
                    pdf=final_pdf(original,dict(e),signers,event['event_hash'])
                    artifact_key=store.put(s['org_id'],pdf)
                    c.execute('INSERT INTO artifacts VALUES(?,?,?,?,?,?)',(uid(),s['org_id'],e['id'],artifact_key,digest(pdf),utc()))
                    append_event(c,s['org_id'],e['id'],'ARTIFACT_CREATED_TEST','system',{'final_sha256':digest(pdf)})
                return {'ok':True,'status':'CONFIRMED_TEST','message':'Confirmação registrada em homologação. Identidade não verificada; sem assinatura ICP-Brasil.'}
        except BaseException:
            if artifact_key:store.remove(artifact_key)
            raise

    @app.get('/api/signers')
    def list_signers(request:Request):
        with db.tx() as c:
            _,o,_=access(c,request)
            return [dict(r) for r in c.execute('SELECT s.id,s.name,s.email,s.status,s.envelope_id,e.title FROM signers s JOIN envelopes e ON e.id=s.envelope_id AND e.org_id=s.org_id WHERE s.org_id=? ORDER BY s.name',(o,))]

    @app.get('/api/templates')
    def templates(request:Request):
        with db.tx() as c:
            _,o,_=access(c,request);return [dict(r) for r in c.execute('SELECT * FROM templates WHERE org_id=? ORDER BY created_at DESC',(o,))]

    @app.post('/api/templates',status_code=201)
    def create_template(body:TemplateInput,request:Request):
        with db.tx() as c:
            u,o,_=access(c,request,write=True);tid=uid()
            c.execute('INSERT INTO templates VALUES(?,?,?,?,?)',(tid,o,body.name,body.body,utc()))
            append_event(c,o,None,'TEMPLATE_CREATED',u['id'],{'template_id':tid})
            return {'id':tid}

    @app.patch('/api/templates/{tid}')
    def update_template(tid:str,body:TemplateInput,request:Request):
        with db.tx() as c:
            u,o,_=access(c,request,write=True)
            cur=c.execute('UPDATE templates SET name=?,body=? WHERE id=? AND org_id=?',(body.name,body.body,tid,o))
            if not cur.rowcount:fail(404,'Modelo não encontrado.')
            append_event(c,o,None,'TEMPLATE_UPDATED',u['id'],{'template_id':tid})
        return {'ok':True}

    @app.delete('/api/templates/{tid}')
    def delete_template(tid:str,request:Request):
        with db.tx() as c:
            u,o,_=access(c,request,write=True)
            cur=c.execute('DELETE FROM templates WHERE id=? AND org_id=?',(tid,o))
            if not cur.rowcount:fail(404,'Modelo não encontrado.')
            append_event(c,o,None,'TEMPLATE_DELETED',u['id'],{'template_id':tid})
        return {'ok':True}

    @app.get('/api/templates/{tid}/pdf')
    def template_pdf(tid:str,request:Request):
        with db.tx() as c:
            _,o,_=access(c,request)
            t=c.execute('SELECT * FROM templates WHERE id=? AND org_id=?',(tid,o)).fetchone()
            if not t:fail(404,'Modelo não encontrado.')
        from reportlab.platypus import SimpleDocTemplate,Paragraph,Spacer
        from reportlab.lib.styles import getSampleStyleSheet
        from html import escape
        out=io.BytesIO();styles=styles_with_fonts()
        story=[Paragraph('HOMOLOGAÇÃO - DOCUMENTO FICTÍCIO',styles['Heading2']),Spacer(1,20),Paragraph(escape(t['name']),styles['Title'])]
        for line in t['body'].splitlines():story.extend([Paragraph(escape(line),styles['BodyText']),Spacer(1,8)])
        SimpleDocTemplate(out).build(story)
        return Response(out.getvalue(),media_type='application/pdf',headers={'Content-Disposition':'attachment; filename="modelo-homologacao.pdf"'})

    @app.get('/api/billing')
    def billing(request:Request):
        with db.tx() as c:
            _,o,_=access(c,request)
            used=c.execute('SELECT COUNT(*) FROM envelopes WHERE org_id=?',(o,)).fetchone()[0]
        return {'plan':'Homologação','envelopes_used':used,'envelope_limit':100,'billing_enabled':False,'message':'Nenhuma cobrança ativa. Planos comerciais aguardam configuração.'}

    @app.post('/api/icp/sign')
    def icp(request:Request):
        with db.tx() as c:access(c,request,write=True)
        fail(501,'ICP-Brasil não configurada. O contrato Java está preparado; nenhuma assinatura digital foi gerada.')

    @app.get('/api/examples/pdf')
    def example_pdf(request:Request):
        with db.tx() as c:user(c,request)
        return FileResponse(BASE/'examples/exemplo-ficticio.pdf',media_type='application/pdf',filename='exemplo-ficticio.pdf')

    @app.get('/')
    @app.get('/app')
    @app.get('/assinar')
    def page():return FileResponse(BASE/'web/index.html')

    @app.get('/assets/{name}')
    def asset(name:str):
        if name not in ('app.js','style.css'):fail(404,'Arquivo não encontrado.')
        return FileResponse(BASE/'web'/name)
    return app
