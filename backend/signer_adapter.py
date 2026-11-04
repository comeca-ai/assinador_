"""Interface for the replaceable Java process. Disabled until integration is validated."""
from typing import Protocol

class SignerAdapter(Protocol):
    def validateCertificateChain(self,certificate:bytes): ...
    def validateSignature(self,pdf:bytes): ...
    def signPades(self,pdf:bytes,credential_ref:str): ...
    def verifyPades(self,pdf:bytes): ...

class DemoiselleSignerAdapter:
    def _disabled(self,*args,**kwargs):
        raise NotImplementedError('ICP-Brasil não configurada; nenhuma assinatura ou validação executada.')
    validateCertificateChain=_disabled
    validateSignature=_disabled
    signPades=_disabled
    verifyPades=_disabled
