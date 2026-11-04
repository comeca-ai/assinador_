"""Explicit runtime settings; containers opt in to a non-loopback bind."""
import os
from urllib.parse import urlsplit

HEALTHCHECK_HOST='healthcheck.railway.app'
LOCAL_HOSTS=('127.0.0.1','localhost','testserver','::1')

def server_options():
    host=os.getenv('ASSINA_HOST','127.0.0.1')
    if host not in ('127.0.0.1','0.0.0.0','::','::1'):
        raise RuntimeError('ASSINA_HOST deve ser um endereço de bind permitido.')
    try:port=int(os.getenv('PORT','8000'))
    except ValueError:raise RuntimeError('PORT deve ser uma porta numérica.') from None
    if not 1<=port<=65535:raise RuntimeError('PORT deve estar entre 1 e 65535.')
    return {'host':host,'port':port}

def resolve_origin(override=None):
    value=override or os.getenv('ASSINA_ORIGIN','http://127.0.0.1:8000')
    parsed=urlsplit(value)
    try:parsed.port
    except ValueError:raise RuntimeError('Porta inválida em ASSINA_ORIGIN.') from None
    if parsed.scheme not in ('http','https') or parsed.path or parsed.query or parsed.fragment or parsed.username or parsed.password or not parsed.hostname:
        raise RuntimeError('ASSINA_ORIGIN deve conter apenas http/https, host e porta, sem barra final.')
    if parsed.scheme=='http' and parsed.hostname not in LOCAL_HOSTS:
        raise RuntimeError('HTTP só é permitido em loopback local.')
    if parsed.hostname==HEALTHCHECK_HOST:
        raise RuntimeError('O host de healthcheck não pode ser usado como origem do aplicativo.')
    return value,parsed
