"""Private AES-256-GCM object store for local homologation. No static mount."""
import io
import os
import secrets
from pathlib import Path
from cryptography.hazmat.primitives.ciphers.aead import AESGCM
from pypdf import PdfReader
from fastapi import HTTPException
from .security import digest, uid

MAX_PDF = 10*1024*1024

class Store:
    def __init__(self, root):
        self.root = Path(root)
        self.root.mkdir(mode=0o700, parents=True, exist_ok=True)
        os.chmod(self.root, 0o700)
        keypath = self.root/'storage.key'
        try:
            fd = os.open(keypath, os.O_WRONLY|os.O_CREAT|os.O_EXCL, 0o600)
            with os.fdopen(fd,'wb') as f: f.write(AESGCM.generate_key(bit_length=256))
        except FileExistsError:
            pass
        self.rate_key = keypath.read_bytes()
        self.crypto = AESGCM(self.rate_key)

    def put(self, org, data):
        # Both segments are server-generated opaque identifiers.
        key = f'{org}/{uid()}'
        path = self.root/key
        path.parent.mkdir(mode=0o700, exist_ok=True)
        nonce = secrets.token_bytes(12)
        with path.open('xb') as f:
            os.chmod(path,0o600)
            f.write(nonce+self.crypto.encrypt(nonce,data,key.encode()))
        return key

    def get(self, key, expected):
        try:
            path = (self.root/key).resolve()
            if not path.is_relative_to(self.root.resolve()):
                raise ValueError('invalid path')
            raw = path.read_bytes()
            data = self.crypto.decrypt(raw[:12], raw[12:], key.encode())
            if digest(data) != expected:
                raise ValueError('digest mismatch')
            return data
        except Exception:
            raise HTTPException(409,'Falha de integridade documental; operação bloqueada.') from None

    def remove(self,key):
        (self.root/key).unlink(missing_ok=True)


def validate_pdf(data):
    if not data.startswith(b'%PDF-') or len(data)>MAX_PDF or len(data)<32:
        raise HTTPException(422,'Envie um PDF de até 10 MB.')
    try:
        pdf = PdfReader(io.BytesIO(data), strict=True)
        if pdf.is_encrypted or not 1 <= len(pdf.pages) <= 100:
            raise ValueError('encrypted or page limit')
        # Reject active constructs, forms, attachments and existing signatures.
        # This is conservative structural validation, NOT an antimalware scanner.
        forbidden = {'/JavaScript','/JS','/Launch','/EmbeddedFiles','/OpenAction','/AA','/AcroForm','/RichMedia','/XFA','/AF','/GoToR','/SubmitForm','/ImportData','/URI'}
        seen = set()
        def inspect(obj, depth=0):
            if depth>60 or len(seen)>50000: raise ValueError('complex PDF')
            if hasattr(obj,'get_object'): obj=obj.get_object()
            if id(obj) in seen: return
            seen.add(id(obj))
            if isinstance(obj,dict):
                if forbidden.intersection(str(k) for k in obj): raise ValueError('active PDF')
                for value in obj.values(): inspect(value,depth+1)
            elif isinstance(obj,list):
                for value in obj: inspect(value,depth+1)
        inspect(pdf.trailer)
        for page in pdf.pages:
            inspect(page)
            if '/Annots' in page: raise ValueError('annotations')
        return len(pdf.pages)
    except Exception:
        raise HTTPException(422,'PDF inválido, protegido, assinado ou com conteúdo ativo. Use PDF simples de teste, até 100 páginas.') from None
