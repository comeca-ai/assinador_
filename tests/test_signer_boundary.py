import os
import secrets
import subprocess
import time
import unittest
import httpx
from pathlib import Path

class JavaBoundaryTest(unittest.TestCase):
    def test_disabled_boundary_and_internal_auth(self):
        root=Path(__file__).resolve().parents[1]
        key=secrets.token_urlsafe(32)
        env={**os.environ,'SIGNER_INTERNAL_TOKEN':key,'SIGNER_PORT':'19091'}
        process=subprocess.Popen(['java',str(root/'services/signer/src/main/java/br/com/assinabrasil/signer/SignerServer.java')],env=env,stdout=subprocess.PIPE,stderr=subprocess.PIPE)
        try:
            with httpx.Client(trust_env=False) as client:
                ready=False
                for _ in range(50):
                    try:
                        r=client.get('http://127.0.0.1:19091/health',headers={'X-Internal-Token':key},timeout=1)
                        if r.status_code==200:ready=True;break
                    except httpx.ConnectError:time.sleep(.1)
                self.assertTrue(ready,'Java boundary did not start')
                self.assertFalse(r.json()['signingEnabled']);self.assertFalse(r.json()['libraryLoaded'])
                self.assertEqual(client.get('http://127.0.0.1:19091/health').status_code,401)
                for name in ['validateCertificateChain','validateSignature','signPades','verifyPades']:
                    r=client.post('http://127.0.0.1:19091/v1/'+name,headers={'X-Internal-Token':key},json={})
                    self.assertEqual(r.status_code,501);self.assertFalse(r.json()['signed']);self.assertFalse(r.json()['verified'])
        finally:
            process.terminate();process.wait(timeout=5)
            if process.stdout:process.stdout.close()
            if process.stderr:process.stderr.close()

if __name__=='__main__':unittest.main()
