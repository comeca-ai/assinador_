"""Loopback probe shared by Docker HEALTHCHECK and local image validation."""
import http.client
import json
import os
import sys

def check():
    connection=http.client.HTTPConnection('127.0.0.1',int(os.getenv('PORT','8000')),timeout=3)
    try:
        connection.request('GET','/api/health',headers={'Host':'healthcheck.railway.app'})
        response=connection.getresponse()
        data=json.loads(response.read())
        return response.status==200 and data.get('status')=='ok' and data.get('mode')=='homologacao' and data.get('production_ready') is False
    except (OSError,ValueError):
        return False
    finally:
        connection.close()

if __name__=='__main__':sys.exit(0 if check() else 1)
