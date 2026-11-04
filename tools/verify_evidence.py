"""Offline verification, no server required. Not a signature/certificate validator."""
import argparse
import json
import sys
from pathlib import Path
sys.path.insert(0,str(Path(__file__).resolve().parents[1]))
from backend.security import verify_manifest
p=argparse.ArgumentParser(description='Verifica cadeia e arquivos de homologação. Não verifica identidade ou ICP-Brasil.')
p.add_argument('manifest');p.add_argument('--original');p.add_argument('--final');args=p.parse_args()
data=json.loads(Path(args.manifest).read_text())
ok=verify_manifest(data,Path(args.original).read_bytes() if args.original else None,Path(args.final).read_bytes() if args.final else None)
print('Consistente nos itens fornecidos. Sem prova de autoria, completude ou tempo confiável.' if ok else 'DIVERGÊNCIA: evidência ou arquivo alterado.')
sys.exit(0 if ok else 1)
