# Assina Brasil

Plataforma própria de documentos e confirmações eletrônicas de **homologação**. Versão 0.2.0, 4 de novembro de 2026. Não publicada e não autorizada para processar documentos reais.

O projeto Lovable foi analisado. A continuação remota ficou bloqueada por falta de créditos e sua geração inicial informou erro de build. Este pacote executável independente foi implementado para continuar o trabalho e permite retomar a integração. O código deste pacote não foi sincronizado com o projeto Lovable. O Supabase habilitado lá ainda não está conectado a esta API.

## Executar localmente

Python 3.12+:

```bash
python3 -m venv .venv
. .venv/bin/activate
python3 -m pip install -r requirements.lock
python3 run.py
```

Abrir http://127.0.0.1:8000. Cadastre uma conta e uma empresa fictícias; não existe senha padrão. Para testar um envelope, baixe o PDF fictício pelo wizard ou use `examples/exemplo-ficticio.pdf`. O servidor escuta em loopback; não o exponha à Internet.

## Implementado

- Landing e aplicativo em português, CSS responsivo, painel, busca/filtros de documentos, wizard de três etapas, detalhe, participantes, modelos CRUD, auditoria, empresas, equipe, marca e quotas.
- API FastAPI; cadastro, login, logout, troca de senha, sessão HttpOnly/CSRF; SQLite persistente, memberships e autorização por empresa.
- PDFs privados com AES-256-GCM e SHA-256; validação estrutural conservadora, preservação do original e recusa de alteração de integridade.
- Links temporários e revogáveis, tokens persistidos por hash, ordem sequencial, consentimento versionado com cópia dos termos, intenção autodeclarada e auditoria encadeada.
- Cópia PDF final marcada como homologação em todas as páginas + relatório, manifesto JSON e verificador offline. Não é PDF assinado digitalmente.
- Serviço Java separado com quatro operações ICP-Brasil desabilitadas, contrato OpenAPI e dependências Demoiselle opcionais. Sem simulação de assinatura ou verificação.

## Verificar

```bash
python3 -m unittest discover -s tests -v
python3 -m compileall -q backend
node --check web/app.js
python3 tools/verify_evidence.py examples/evidencias-exemplo.json --original examples/exemplo-ficticio.pdf --final examples/exemplo-final-homologacao.pdf
```

Veja `docs/TESTES.md` para resultados efetivamente executados e limites. A prévia de navegador da sessão estava indisponível; validação visual/interativa desktop e mobile não foi concluída.

## Arquivos e estado

- `backend/`: API, domínio, esquema, autenticação, armazenamento e evidências.
- `web/`: interface servida pela própria API, sem build ou bibliotecas JS externas.
- `services/signer/`: fronteira Java desabilitada e POM opcional Demoiselle.
- `contracts/`: OpenAPI real da plataforma, contrato Java e proposta de webhook.
- `tests/`: testes de integração, concorrência, permissões e integridade.
- `examples/`: PDFs e manifesto fictícios produzidos pelo fluxo da API.
- `tools/`: geração de exemplo e verificação offline.
- `docs/`: arquitetura, operação, segurança, status, testes e retomada do Lovable.

Os dados e chaves locais surgem em `runtime/`, ignorado no versionamento e excluído da entrega. O código original tem licença proprietária no arquivo LICENSE; bibliotecas e fontes mantêm suas próprias licenças, conforme THIRD_PARTY_NOTICES.md. Demoiselle não está incorporado ou carregado nesta versão.

## Antes de produção

Ainda faltam PostgreSQL/RLS e armazenamento gerenciado, identificação de signatários, recuperação/verificação de e-mail e MFA, scanner PDF isolado, KMS/rotação, restauração sob falha, âncora externa/WORM, revisão independente e jurídica. ICP-Brasil real, pagamentos, API comercial e entrega de webhooks não estão implementados. Não foi criado domínio ou deployment de produção.
