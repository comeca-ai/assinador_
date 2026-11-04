# Correção do build no Railway - homologação

## Diagnóstico observado
Em 04/11/2026 foi inspecionado o deployment `197238b4-fd07-4748-9328-d2a2b5c3fb46`, serviço `assinador_`, repositório `comeca-ai/assinador_`, commit `09f2534ca1b24353a1000bab4f800f844bcff2a0`.

A falha ocorreu na preparação do Railpack v0.43.0. Os logs mostram apenas unpacking, download do driver e upload do snapshot. Não há mensagem que demonstre a causa interna exata. O código tinha `package.json` auxiliar sem start/main/index e uma API Python criada por factory em `backend.app:create_app`; não corresponde ao entrypoint FastAPI padrão `main:app`. Isso é uma incompatibilidade de configuração observável, não comprovação da causa interna do Railpack.

## Correção implementada
- Dockerfile na raiz explicita Python 3.12, dependências bloqueadas e comando `python run.py`. O Railway detecta esse arquivo sem depender da escolha automática Node/Python do Railpack.
- O frontend é servido pela API e não exige npm install, Vite ou comando de build Node.
- `ASSINA_HOST` permite bind 0.0.0.0 no container; execução local segue 127.0.0.1. `PORT` é lida e validada, sem fixar a porta injetada pelo Railway.
- Healthcheck em `/api/health` aceita o Host `healthcheck.railway.app` somente nessa rota GET; outros recursos continuam inacessíveis por esse Host. Probes não consomem rate limit de usuários.
- A imagem roda como UID/GID 10001 e não inclui banco, chaves, `.env`, testes ou código Java. O motor ICP-Brasil continua separado e desabilitado.
- Workflow de PR valida testes e constrói/testa a imagem sem deploy.

## Configuração do serviço ao aplicar a correção

| Campo | Valor |
| --- | --- |
| Source | `comeca-ai/assinador_`, revisão que contém esta correção |
| Root Directory | raiz `/` (Dockerfile e requirements.lock na raiz) |
| Builder | Dockerfile detectado automaticamente |
| Custom Build Command | vazio |
| Custom Start Command | vazio (usa CMD do Dockerfile) |
| Healthcheck Path | `/api/health` |
| Réplicas | 1 enquanto usar SQLite local |
| ASSINA_MODE | `homologacao` |
| ASSINA_HOST | `0.0.0.0` (já definido na imagem) |
| ASSINA_DATA | `/data` (já definido na imagem) |
| ASSINA_ORIGIN | origem HTTPS exata usada na homologação, sem barra final |
| Volume | montar em `/data`, gravável pelo UID/GID 10001 |

`PORT` é fornecida pela plataforma. Não inventar domínio: configurar ASSINA_ORIGIN com a origem real quando ela existir. `http://127.0.0.1:8000` continua sendo o padrão local; sem ASSINA_ORIGIN, a interface não aceitará outro Host/origem. O probe de saúde funciona independentemente da origem da interface.

Um volume persistente é necessário antes de guardar qualquer registro: sem ele, recriar o container perde banco e chave dos PDFs. A montagem pode substituir as permissões preparadas na imagem; garantir a permissão do UID/GID 10001 no volume. Não contornar erro de permissão usando armazenamento efêmero ou alterando os controles do aplicativo. Não há migração automática para PostgreSQL neste patch.

Não foi criado railway.json/railway.toml: o serviço nunca usou Config as Code, e a documentação/UI atual indicam que novos usos desse mecanismo legado não são aceitos. A configuração acima usa o Dockerfile e campos do serviço.

## Por que não há redeploy automático desta correção
O Railway está conectado à branch main, com auto deploy ativo, no ambiente chamado production. A correção é preparada em uma branch/PR. Ela não autoriza merge ou publicação de produção: permanece a instrução do projeto de validar segurança, integridade e auditoria antes disso. O serviço inspecionado não possui domínio público.

## Validação
Ver `docs/railway-test-results.txt` e a execução de CI do PR. No executor desta sessão não há Docker/BuildKit nem CLI Railpack, portanto não se declara imagem local construída. O workflow fornece build da imagem em runner com Docker, quando habilitado no repositório. Nenhuma etapa de CI faz deploy ou gera domínio.

## Fontes oficiais consultadas
- https://docs.railway.com/builds/dockerfiles
- https://docs.railway.com/deployments/healthchecks
- https://docs.railway.com/config-as-code
- https://railpack.com/languages/node/
- https://railpack.com/languages/python/
