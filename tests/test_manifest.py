import copy
import json
import unittest
from pathlib import Path
from backend.security import verify_manifest

class ManifestTest(unittest.TestCase):
    def test_offline_evidence_commitments_and_document_tampering(self):
        root=Path(__file__).resolve().parents[1]/'examples'
        data=json.loads((root/'evidencias-exemplo.json').read_text())
        original=(root/'exemplo-ficticio.pdf').read_bytes();final=(root/'exemplo-final-homologacao.pdf').read_bytes()
        self.assertTrue(verify_manifest(data,original,final))
        self.assertFalse(verify_manifest(data,original+b'changed',final))
        changed=copy.deepcopy(data);changed['final_sha256']='0'*64;self.assertFalse(verify_manifest(changed))
        changed=copy.deepcopy(data);changed['signers'][0]['declared_name']='Other';self.assertFalse(verify_manifest(changed))
        changed=copy.deepcopy(data);changed['consents'][0]['terms_text']='Altered';self.assertFalse(verify_manifest(changed))
