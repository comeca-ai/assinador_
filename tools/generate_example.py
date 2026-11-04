"""Reproducible API integration example, using only fictitious temporary data."""
import json
import sys
import tempfile
from pathlib import Path
from fastapi.testclient import TestClient
sys.path.insert(0,str(Path(__file__).resolve().parents[1]))
from backend.app import create_app

from create_example_pdf import create
create()
root=Path(__file__).resolve().parents[1]
with tempfile.TemporaryDirectory() as tmp:
    app=create_app(tmp,'http://testserver')
    with TestClient(app) as c:
        c.headers['Origin']='http://testserver'
        r=c.post('/api/auth/register',json={'name':'Pessoa Fictícia','email':'exemplo@example.com','password':'senha-ficticia-apenas-teste','organization':'Empresa Fictícia'})
        r.raise_for_status();me=c.get('/api/me').json()
        c.headers.update({'X-CSRF-Token':me['csrf'],'X-Organization':me['organizations'][0]['id']})
        r=c.post('/api/envelopes',data={'title':'Termo de homologação - documento fictício','test_only':'true'},files={'file':('exemplo.pdf',(root/'examples/exemplo-ficticio.pdf').read_bytes(),'application/pdf')})
        r.raise_for_status();eid=r.json()['id']
        r=c.post(f'/api/envelopes/{eid}/signers',json={'name':'Pessoa Fictícia','email':'participante@example.com'});r.raise_for_status();sid=r.json()['id']
        c.post(f'/api/envelopes/{eid}/send',json={}).raise_for_status()
        t=c.post(f'/api/envelopes/{eid}/links/{sid}',json={}).json()['url'].split('#')[1]
        d=c.post('/api/signing/open',json={'token':t}).json()
        c.post('/api/signing/consent',json={'token':t,'accepted':True,'terms_version':d['terms_version']}).raise_for_status()
        c.post('/api/signing/confirm',json={'token':t,'declared_name':'Pessoa Fictícia','original_sha256':d['original_sha256']}).raise_for_status()
        pdf=c.get(f'/api/envelopes/{eid}/artifact');pdf.raise_for_status()
        evidence=c.get(f'/api/envelopes/{eid}/evidence');evidence.raise_for_status()
        (root/'examples/exemplo-final-homologacao.pdf').write_bytes(pdf.content)
        (root/'examples/evidencias-exemplo.json').write_text(json.dumps(evidence.json(),ensure_ascii=False,indent=2)+'\n')
        (root/'contracts/platform.openapi.json').write_text(json.dumps(app.openapi(),ensure_ascii=False,indent=2)+'\n')
print('Exemplo de homologação e OpenAPI gerados; nenhum dado operacional foi criado.')
