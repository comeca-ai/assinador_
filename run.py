import uvicorn
from backend.config import server_options

if __name__=='__main__':
    uvicorn.run('backend.app:create_app',factory=True,**server_options(),access_log=False,proxy_headers=False)
