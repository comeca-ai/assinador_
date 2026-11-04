import io
import json
import sys
import tempfile
import time
import unittest
from concurrent.futures import ThreadPoolExecutor
from pathlib import Path
from fastapi.testclient import TestClient
from reportlab.pdfgen import canvas
from pypdf import PdfReader, PdfWriter
from pypdf.generic import NameObject, TextStringObject, DictionaryObject
sys.path.insert(0,str(Path(__file__).resolve().parents[1]))
from backend.app import create_app
from backend.security import digest,verify_chain,canonical,event_hash

ORIGIN='http://testserver'
PASSWORD='senha-ficticia-longa-2026'

def pdf_bytes():
    out=io.BytesIO();c=canvas.Canvas(out);c.drawString(50,750,'DOCUMENTO FICTICIO - HOMOLOGACAO');c.drawString(50,720,'Sem efeito juridico. Apenas para testar o Assina Brasil.');c.save();return out.getvalue()

class PlatformFixtures(unittest.TestCase):
    def setUp(self):
        self.tmp=tempfile.TemporaryDirectory();self.app=create_app(self.tmp.name,ORIGIN)
        self.a=TestClient(self.app);self.b=TestClient(self.app)
        self.register(self.a,'a@example.com','Empresa A')
        self.register(self.b,'b@example.com','Empresa B')
        self.oa=self.a.get('/api/me').json()['organizations'][0]['id']
        self.ob=self.b.get('/api/me').json()['organizations'][0]['id']
        self.public=TestClient(self.app)
    def tearDown(self):
        for c in [self.a,self.b,self.public]:c.close()
        self.tmp.cleanup()
    def register(self,c,email,org):
        r=c.post('/api/auth/register',headers={'Origin':ORIGIN},json={'email':email,'password':PASSWORD,'name':'Pessoa Ficticia','organization':org});self.assertEqual(r.status_code,201,r.text)
        me=c.get('/api/me').json();c.headers.update({'Origin':ORIGIN,'X-CSRF-Token':me['csrf'],'X-Organization':me['organizations'][0]['id']})
    def post(self,path,body):return self.public.post(path,headers={'Origin':ORIGIN},json=body)
    def envelope(self,client=None,ordered=False,n=1):
        c=client or self.a;r=c.post('/api/envelopes',data={'title':'Termo ficticio','test_only':'true','ordered':str(ordered),'days':7},files={'file':('teste.pdf',pdf_bytes(),'application/pdf')});self.assertEqual(r.status_code,201,r.text);eid=r.json()['id'];signers=[]
        for i in range(n):
            r=c.post(f'/api/envelopes/{eid}/signers',json={'name':f'Pessoa Teste {i+1}','email':f'teste{i}@example.com'});self.assertEqual(r.status_code,201,r.text);signers.append(r.json()['id'])
        return eid,signers
    def available(self,ordered=False,n=1):
        eid,sids=self.envelope(ordered=ordered,n=n)
        self.assertEqual(self.a.post(f'/api/envelopes/{eid}/send',json={}).status_code,200)
        tokens=[self.a.post(f'/api/envelopes/{eid}/links/{s}',json={}).json()['url'].split('#')[1] for s in sids]
        return eid,sids,tokens
    def accept(self,t):
        d=self.post('/api/signing/open',{'token':t}).json()
        r=self.post('/api/signing/consent',{'token':t,'accepted':True,'terms_version':d['terms_version']});self.assertEqual(r.status_code,200,r.text)
        return d
    def confirm(self,t,d):return self.post('/api/signing/confirm',{'token':t,'declared_name':'Pessoa Ficticia','original_sha256':d['original_sha256']})

class PlatformTests(PlatformFixtures):
    def test_auth_session_and_csrf(self):
        self.assertEqual(TestClient(self.app).get('/api/me').status_code,401)
        self.assertIn('HttpOnly',self.a.cookies.get('assina_session') and self.a.post('/api/auth/login',json={'email':'a@example.com','password':PASSWORD}).headers['set-cookie'])
        self.assertEqual(self.a.patch('/api/organization',headers={'X-CSRF-Token':'wrong'},json={'brand_name':'Marca X','color':'#123456'}).status_code,403)
        self.assertEqual(self.a.post('/api/organizations',headers={'Origin':'https://evil.example'},json={'name':'Qualquer'}).status_code,403)
        self.assertEqual(self.a.post('/api/auth/login',json={'email':'a@example.com','password':'senha-errada-1234'}).status_code,401)
    def test_tenant_isolation_all_resources(self):
        eid,_=self.envelope()
        for path in [f'/api/envelopes/{eid}',f'/api/envelopes/{eid}/pdf',f'/api/envelopes/{eid}/artifact',f'/api/envelopes/{eid}/evidence']:
            self.assertEqual(self.b.get(path).status_code,404,path)
        self.assertEqual(self.b.get('/api/envelopes',headers={'X-Organization':self.oa}).status_code,404)
        self.assertEqual(self.b.post(f'/api/envelopes/{eid}/signers',json={'name':'Pessoa Invasora','email':'x@example.com'}).status_code,404)
        tid=self.a.post('/api/templates',json={'name':'Modelo A','body':'Texto ficticio de teste.'}).json()['id']
        self.assertEqual(self.b.get('/api/templates').json(),[])
        self.assertEqual(self.b.patch('/api/templates/'+tid,json={'name':'Outro','body':'Nao permitido'}).status_code,404)
        self.assertEqual(self.b.get('/api/templates/'+tid+'/pdf').status_code,404)
    def test_viewer_cannot_write_or_escalate(self):
        self.assertEqual(self.a.post('/api/members',json={'email':'b@example.com','role':'viewer'}).status_code,200)
        headers={'X-Organization':self.oa}
        self.assertEqual(self.b.get('/api/envelopes',headers=headers).status_code,200)
        self.assertEqual(self.b.post('/api/templates',headers=headers,json={'name':'Outro','body':'Nao permitido'}).status_code,403)
        self.assertEqual(self.b.post('/api/members',headers=headers,json={'email':'b@example.com','role':'admin'}).status_code,403)
        self.assertEqual(self.b.patch('/api/organization',headers=headers,json={'brand_name':'Outra','color':'#123456'}).status_code,403)
    def test_admin_cannot_elevate_self(self):
        self.a.post('/api/members',json={'email':'b@example.com','role':'admin'})
        self.assertEqual(self.b.post('/api/members',headers={'X-Organization':self.oa},json={'email':'b@example.com','role':'admin'}).status_code,403)
    def test_pdf_validation_and_private_encryption(self):
        for data,mime in [(b'not a pdf','application/pdf'),(pdf_bytes(),'image/png')]:
            r=self.a.post('/api/envelopes',data={'title':'Teste','test_only':'true'},files={'file':('x.pdf',data,mime)});self.assertEqual(r.status_code,422,r.text)
        writer=PdfWriter();writer.add_blank_page(width=100,height=100);writer.add_js("app.alert('test')");out=io.BytesIO();writer.write(out)
        r=self.a.post('/api/envelopes',data={'title':'Ativo','test_only':'true'},files={'file':('x.pdf',out.getvalue(),'application/pdf')});self.assertEqual(r.status_code,422)
        eid,_=self.envelope()
        with self.app.state.db.tx() as db:e=db.execute('SELECT * FROM envelopes WHERE id=?',(eid,)).fetchone();key=e['original_key']
        raw=(Path(self.tmp.name)/'objects'/key).read_bytes()
        self.assertFalse(raw.startswith(b'%PDF'));self.assertNotIn(b'DOCUMENTO FICTICIO',raw)
        self.assertTrue(self.a.get('/api/envelopes/'+eid+'/pdf').content.startswith(b'%PDF'))
        self.assertEqual(self.a.get('/runtime/objects/'+key).status_code,404)
    def test_token_hashed_reissued_revoked_and_invalid(self):
        eid,sids,tokens=self.available();t=tokens[0]
        with self.app.state.db.tx() as db:
            row=dict(db.execute('SELECT * FROM signing_sessions').fetchone());self.assertEqual(row['token_hash'],digest(t));self.assertNotIn(t,str(row))
        t2=self.a.post(f'/api/envelopes/{eid}/links/{sids[0]}',json={}).json()['url'].split('#')[1]
        self.assertEqual(self.post('/api/signing/open',{'token':t}).status_code,404)
        self.a.post(f'/api/envelopes/{eid}/revoke/{sids[0]}',json={})
        self.assertEqual(self.post('/api/signing/open',{'token':t2}).status_code,404)
        self.assertEqual(self.post('/api/signing/open',{'token':'A'*43}).status_code,404)
    def test_expired_session_and_envelope(self):
        eid,sids,tokens=self.available()
        with self.app.state.db.tx() as db:db.execute('UPDATE signing_sessions SET expires_at=?',(time.time()-1,))
        self.assertEqual(self.post('/api/signing/open',{'token':tokens[0]}).status_code,404)
        t=self.a.post(f'/api/envelopes/{eid}/links/{sids[0]}',json={}).json()['url'].split('#')[1]
        with self.app.state.db.tx() as db:db.execute('UPDATE envelopes SET expires_at=?',(time.time()-1,))
        self.assertEqual(self.post('/api/signing/open',{'token':t}).status_code,404)
    def test_consent_hash_and_replay(self):
        eid,_,tokens=self.available();t=tokens[0];d=self.post('/api/signing/open',{'token':t}).json()
        self.assertEqual(self.confirm(t,d).status_code,422)
        self.assertEqual(self.post('/api/signing/consent',{'token':t,'accepted':True,'terms_version':'old'}).status_code,422)
        d=self.accept(t)
        self.assertEqual(self.confirm(t,{**d,'original_sha256':'0'*64}).status_code,409)
        r=self.confirm(t,d);self.assertEqual(r.status_code,200,r.text)
        self.assertEqual(self.confirm(t,d).status_code,404)
        self.assertEqual(self.post('/api/signing/pdf',{'token':t}).status_code,404)
        self.assertEqual(self.a.get('/api/envelopes/'+eid).json()['status'],'COMPLETED_TEST')
    def test_ordering_is_enforced(self):
        eid,_,tokens=self.available(ordered=True,n=2)
        self.assertEqual(self.post('/api/signing/open',{'token':tokens[1]}).status_code,409)
        self.assertEqual(self.confirm(tokens[0],self.accept(tokens[0])).status_code,200)
        self.assertEqual(self.a.get('/api/envelopes/'+eid).json()['status'],'IN_PROGRESS')
        self.assertEqual(self.confirm(tokens[1],self.accept(tokens[1])).status_code,200)
    def test_tampered_original_rejected_without_consumption(self):
        eid,_,tokens=self.available();t=tokens[0];d=self.accept(t)
        with self.app.state.db.tx() as db:e=dict(db.execute('SELECT * FROM envelopes WHERE id=?',(eid,)).fetchone())
        path=Path(self.tmp.name)/'objects'/e['original_key'];raw=path.read_bytes();path.write_bytes(raw[:-1]+bytes([raw[-1]^1]))
        self.assertEqual(self.confirm(t,d).status_code,409)
        with self.app.state.db.tx() as db:
            row=db.execute('SELECT consumed_at FROM signing_sessions WHERE token_hash=?',(digest(t),)).fetchone();self.assertIsNone(row[0])
            self.assertEqual(db.execute('SELECT COUNT(*) FROM artifacts').fetchone()[0],0)
    def test_concurrent_confirm_once_and_artifact_integrity(self):
        eid,_,tokens=self.available();t=tokens[0];d=self.accept(t)
        def confirm_once(_):
            with TestClient(self.app) as client:return client.post('/api/signing/confirm',headers={'Origin':ORIGIN},json={'token':t,'declared_name':'Pessoa Ficticia','original_sha256':d['original_sha256']}).status_code
        with ThreadPoolExecutor(max_workers=2) as pool:results=list(pool.map(confirm_once,range(2)))
        self.assertEqual(sorted(results),[200,404])
        detail=self.a.get('/api/envelopes/'+eid).json();pdf=self.a.get('/api/envelopes/'+eid+'/artifact').content
        self.assertEqual(digest(pdf),detail['artifact']['sha256'])
        text='\n'.join(page.extract_text() for page in PdfReader(io.BytesIO(pdf)).pages)
        self.assertIn('HOMOLOGACAO',text);self.assertIn('ICP-BRASIL',text)
        evidence=self.a.get('/api/envelopes/'+eid+'/evidence').json();self.assertTrue(verify_chain(evidence['events']))
        self.assertFalse(evidence['identity_verified']);self.assertEqual(evidence['final_sha256'],digest(pdf))
        with self.app.state.db.tx() as db:
            self.assertEqual(db.execute('SELECT COUNT(*) FROM artifacts').fetchone()[0],1)
            self.assertEqual(db.execute('SELECT COUNT(*) FROM audit_events WHERE event_type="INTENT_CONFIRMED_TEST"').fetchone()[0],1)
            a=dict(db.execute('SELECT * FROM artifacts').fetchone())
        p=Path(self.tmp.name)/'objects'/a['storage_key'];raw=p.read_bytes();p.write_bytes(raw[:-1]+bytes([raw[-1]^1]))
        self.assertEqual(self.a.get('/api/envelopes/'+eid+'/artifact').status_code,409)
    def test_audit_append_only_and_tamper_detection(self):
        self.envelope();a=self.a.get('/api/audit').json();self.assertTrue(a['chain_valid'])
        altered=[dict(e) for e in a['events']];altered[0]['actor']='other';self.assertFalse(verify_chain(altered))
        self.assertFalse(verify_chain(a['events'][1:]))
        with self.assertRaises(Exception):
            with self.app.state.db.tx() as db:db.execute('UPDATE audit_events SET actor="changed"')
        with self.assertRaises(Exception):
            with self.app.state.db.tx() as db:db.execute('DELETE FROM audit_events')
    def test_cancel_revokes_and_state_transitions(self):
        eid,sids,tokens=self.available()
        self.assertEqual(self.a.post('/api/envelopes/'+eid+'/signers',json={'name':'Outra','email':'other@example.com'}).status_code,409)
        self.assertEqual(self.a.post('/api/envelopes/'+eid+'/send',json={}).status_code,409)
        self.assertEqual(self.a.post('/api/envelopes/'+eid+'/cancel',json={}).status_code,200)
        self.assertEqual(self.post('/api/signing/open',{'token':tokens[0]}).status_code,404)
    def test_brand_multi_org_and_template_crud(self):
        self.assertEqual(self.a.patch('/api/organization',json={'brand_name':'Marca Ficticia','color':'#123456'}).status_code,200)
        self.assertEqual(self.a.get('/api/me').json()['organizations'][0]['brand_name'],'Marca Ficticia')
        o=self.a.post('/api/organizations',json={'name':'Empresa C'}).json()['id']
        self.assertEqual(self.a.get('/api/envelopes',headers={'X-Organization':o}).json(),[])
        tid=self.a.post('/api/templates',json={'name':'Modelo Teste','body':'Conteudo inteiramente ficticio.'}).json()['id']
        self.assertEqual(self.a.patch('/api/templates/'+tid,json={'name':'Alterado','body':'Texto alterado de teste.'}).status_code,200)
        pdf=self.a.get('/api/templates/'+tid+'/pdf');self.assertEqual(pdf.status_code,200);self.assertTrue(pdf.content.startswith(b'%PDF'))
        self.assertEqual(self.a.request('DELETE','/api/templates/'+tid,json={}).status_code,200)
    def test_rate_limit_and_no_sensitive_error_echo(self):
        token_value='A'*43
        r=self.post('/api/signing/confirm',{'token':token_value,'declared_name':'X','original_sha256':'bad'})
        self.assertEqual(r.status_code,422);self.assertNotIn(token_value,r.text)
        for _ in range(101):r=self.post('/api/signing/open',{'token':token_value})
        self.assertEqual(r.status_code,429)
    def test_unimplemented_integrations_fail_closed(self):
        self.assertEqual(self.a.post('/api/icp/sign',json={}).status_code,501)
        self.assertEqual(self.a.post('/api/auth/recover',json={}).status_code,503)
        self.assertFalse(self.a.get('/api/billing').json()['billing_enabled'])
    def test_security_headers_and_document_body_limit(self):
        r=self.a.get('/');self.assertEqual(r.status_code,200)
        self.assertEqual(r.headers['referrer-policy'],'no-referrer')
        self.assertIn("script-src 'self'",r.headers['content-security-policy'])
        r=self.a.post('/api/envelopes',content=b'x'*(11*1024*1024),headers={'Content-Type':'multipart/form-data; boundary=test'})
        self.assertEqual(r.status_code,413)
    def test_remove_signer_gap_can_add(self):
        eid,sids=self.envelope(n=2)
        self.assertEqual(self.a.request('DELETE',f'/api/envelopes/{eid}/signers/{sids[0]}',json={}).status_code,200)
        self.assertEqual(self.a.post('/api/envelopes/'+eid+'/signers',json={'name':'Terceiro Teste','email':'terceiro@example.com'}).status_code,201)
    def test_password_change_invalidates_sessions(self):
        second=TestClient(self.app)
        login=second.post('/api/auth/login',headers={'Origin':ORIGIN},json={'email':'a@example.com','password':PASSWORD});self.assertEqual(login.status_code,200)
        r=self.a.post('/api/auth/password',json={'current_password':PASSWORD,'new_password':'nova-senha-ficticia-2026'});self.assertEqual(r.status_code,200)
        self.assertEqual(second.get('/api/me').status_code,401);self.assertEqual(self.a.get('/api/me').status_code,401)
        second.close()

if __name__=='__main__':unittest.main(verbosity=2)
