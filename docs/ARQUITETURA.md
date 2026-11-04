# Arquitetura implementada - 0.2.0 (homologação)

## Situação do projeto existente
O projeto Lovable `707da202-a3f6-4baf-974a-0ae112895b9e` foi inspecionado pelo conector. O commit da geração inicial é `8a90219a29c7497a3ffc707967c4ab6e250b8f80`: React/TypeScript, TanStack Start, Tailwind e serviços em memória. A geração informou build quebrado e não houve navegação validada. Nenhuma alteração remota adicional de código foi aceita: o workspace está sem créditos. O banco Supabase foi habilitado, mas não recebeu tabelas ou dados desta implementação.

Esta entrega é uma implementação independente, executável e portável, baseada na documentação anexada e nos fluxos analisados. Ela não foi sincronizada com o Lovable. Não há publicação de produção ou migração silenciosa de dados.

## Camadas executáveis

| Camada | Arquivos | Comportamento |
| --- | --- | --- |
| Web | `web/index.html`, `web/app.js`, `web/style.css` | Landing, contas, painel, documentos, wizard, detalhe, signatários, modelos, auditoria, marca, empresas e quotas; sem dependências JS externas |
| API | `backend/app.py`, `models.py` | FastAPI, validação estrita, controle de sessão/CSRF e autorização por empresa |
| Dados | `backend/schema.sql`, `db.py` | SQLite local com chaves estrangeiras compostas, transações BEGIN IMMEDIATE e triggers append-only |
| Integridade | `backend/security.py` | scrypt, tokens aleatórios, SHA-256 e cadeia de eventos canônica |
| Documentos | `storage.py`, `evidence.py` | Objetos privados AES-256-GCM; PDF original preservado; cópia final de homologação marcada e relatório |
| ICP-Brasil | `services/signer/`, `signer_adapter.py` | Fronteira Java executável, autenticação interna e respostas 501; biblioteca ainda não carregada |

O SQLite foi escolhido para permitir testar e executar sem credenciais ou rede. Não é o PostgreSQL/Supabase habilitado no Lovable. A migração para PostgreSQL, RLS e object storage gerenciado permanece pendente; não se declara RLS onde o isolamento é feito pela API.

## Isolamento
Cada requisição autenticada resolve o usuário pela sessão opaca, procura membership para o `X-Organization` solicitado e verifica o papel. Um ID de organização enviado pelo browser não concede acesso. Toda busca de envelope/modelo é filtrada por tenant. Arquivos não têm rota estática; são descriptografados somente após autorização ou resolução de token de participante.

`owner` administra a empresa; `admin` configura marca/equipe, sem atribuir administração nem alterar o proprietário; `member` opera documentos e modelos; `viewer` apenas consulta. Todos os membros com leitura veem os documentos da empresa: não há ACL por documento nesta versão.

## Máquina de estados
DRAFT → SENT → IN_PROGRESS → COMPLETED_TEST. DRAFT/SENT/IN_PROGRESS podem ir para CANCELED. A expiração é verificada contra o relógio do servidor em cada operação; a UI deriva EXPIRED, sem job de transição permanente. Signatários só são alterados no rascunho.

## Link e evidência
1. Usuário autorizado disponibiliza o envelope e emite link manual por participante. Nenhum e-mail é enviado.
2. Token CSPRNG de 32 bytes em fragmento da URL; apenas SHA-256 persiste. A UI remove o fragmento do histórico imediatamente após carregá-lo. Isso reduz exposição ao servidor; não é promessa de apagar sincronizações anteriores do navegador.
3. Sessão expira em até 24 horas, limitada ao prazo do envelope. Reemissão revoga o anterior. Ordem sequencial é aplicada no servidor.
4. A API verifica PDF/hash, registra abertura e busca do PDF. Não diz que um download prova leitura humana.
5. Consentimento guarda versão, hash dos termos e horário UTC. A confirmação exige esse consentimento e o hash do PDF revisado.
6. Uma transação consome o token e registra a intenção. Replay é recusado; os efeitos não se duplicam. A última confirmação gera um único PDF de homologação, hash e evento de artefato.

Cadeia SHA-256 por organização: `SHA256(JSON canônico de id,org_id,envelope_id,event_type,actor,time_utc,payload,prev_event_hash))`. `payload` é uma string JSON canônica. UTF-8, chaves ordenadas, sem espaços, sem NaN. O manifesto inclui toda a cadeia da empresa para permitir verificação; não compartilhe o manifesto entre empresas. O relatório inclui a cabeça da cadeia no evento de conclusão; o hash final entra no evento seguinte, evitando autorreferência.

## Limites transacionais
Arquivo é escrito de forma exclusiva antes do commit; erro tratado remove arquivo órfão. Uma queda abrupta entre gravação e commit ainda pode deixar órfãos, exigindo reconciliação operacional. O wizard usa chamadas sequenciais e preserva rascunho se uma etapa falhar: não simula atomicidade entre upload e todos os participantes.

## Próximas infraestruturas
PostgreSQL com RLS e papéis mínimos, scanner PDF em sandbox com limites de CPU, object storage privado/KMS, fila/outbox transacional, âncora externa/WORM, OTP/MFA, SMTP e monitoramento. O servidor local recusa `ASSINA_MODE` diferente de `homologacao`; essa trava não substitui a validação técnica e jurídica.
