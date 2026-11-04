import os
import unittest
from unittest.mock import patch
from fastapi.testclient import TestClient
from backend.config import server_options,resolve_origin,HEALTHCHECK_HOST
import test_platform as platform

class RuntimeConfigTest(unittest.TestCase):
    def test_local_default_and_container_port(self):
        with patch.dict(os.environ,{},clear=True):
            self.assertEqual(server_options(),{'host':'127.0.0.1','port':8000})
        with patch.dict(os.environ,{'ASSINA_HOST':'0.0.0.0','PORT':'8097'},clear=True):
            self.assertEqual(server_options(),{'host':'0.0.0.0','port':8097})
    def test_invalid_port_and_origin_fail_closed(self):
        for value in ('bad','0','65536'):
            with patch.dict(os.environ,{'PORT':value},clear=True):
                with self.assertRaises(RuntimeError):server_options()
        for value in ('ftp://localhost','http://public.example','https://example.com/path','https://a:b@example.com','https://example.com:bad','https://'+HEALTHCHECK_HOST):
            with self.assertRaises(RuntimeError):resolve_origin(value)
        self.assertEqual(resolve_origin('https://homolog.example')[0],'https://homolog.example')

class HealthHostTest(platform.PlatformFixtures):
    def test_platform_health_probe_does_not_open_other_routes(self):
        with TestClient(self.app) as c:
            for _ in range(105):
                self.assertEqual(c.get('/api/health',headers={'Host':HEALTHCHECK_HOST}).status_code,200)
            self.assertEqual(c.get('/api/me',headers={'Host':HEALTHCHECK_HOST}).status_code,400)
            self.assertEqual(c.get('/',headers={'Host':HEALTHCHECK_HOST}).status_code,400)
            self.assertEqual(c.post('/api/health',headers={'Host':HEALTHCHECK_HOST}).status_code,400)
            self.assertEqual(c.get('/api/health',headers={'Host':'evil.example'}).status_code,400)
            self.assertEqual(c.get('/api/envelopes',headers={'Host':'testserver'}).status_code,401)


class RealServerTest(unittest.TestCase):
    def test_boot_on_platform_port_and_health_script(self):
        import http.client
        import socket
        import subprocess
        import sys
        import tempfile
        import time
        from pathlib import Path
        root=Path(__file__).resolve().parents[1]
        with socket.socket() as sock:
            sock.bind(('127.0.0.1',0));port=sock.getsockname()[1]
        with tempfile.TemporaryDirectory() as temp:
            env={**os.environ,'ASSINA_HOST':'0.0.0.0','PORT':str(port),'ASSINA_DATA':temp,'ASSINA_ORIGIN':'https://homolog.example','ASSINA_MODE':'homologacao'}
            process=subprocess.Popen([sys.executable,'run.py'],cwd=root,env=env,stdout=subprocess.DEVNULL,stderr=subprocess.PIPE)
            try:
                ready=False
                for _ in range(50):
                    try:
                        conn=http.client.HTTPConnection('127.0.0.1',port,timeout=1)
                        conn.request('GET','/api/health',headers={'Host':HEALTHCHECK_HOST})
                        response=conn.getresponse();response.read();conn.close()
                        if response.status==200:ready=True;break
                    except OSError:time.sleep(.1)
                self.assertTrue(ready,'Application did not bind to PORT')
                result=subprocess.run([sys.executable,'tools/healthcheck.py'],cwd=root,env=env,timeout=5,check=False)
                self.assertEqual(result.returncode,0)
                conn=http.client.HTTPConnection('127.0.0.1',port,timeout=2)
                conn.request('GET','/',headers={'Host':'homolog.example'})
                response=conn.getresponse();self.assertEqual(response.status,200);self.assertIn(b'Assina Brasil',response.read());conn.close()
            finally:
                process.terminate();process.wait(timeout=5)
                if process.stderr:process.stderr.close()
