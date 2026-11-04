# Execução e operação de homologação

## Executar
Requisitos: Python 3.12+, Node apenas para checagem JS e Java 17+ para o serviço de fronteira. Testado no runtime Python 3.12 e OpenJDK 21. Não há npm install ou build de frontend: os assets são servidos pela própria API.

```bash
python3 -m venv .venv
. .venv/bin/activate
python3 -m pip install -r requirements.lock
python3 run.py
```

Abrir http://127.0.0.1:8000. O servidor escuta exclusivamente em loopback. Cadastre conta fictícia pela interface; não há senha padrão nem dados seed. A referência HTML local da API fica em `/api/docs`, sem dependências de CDN. O contrato completo está em `/api/openapi.json` e `contracts/platform.openapi.json`. É documentação de consulta, sem console de execução.

Configuração opcional: `ASSINA_DATA` muda o diretório de dados, `PORT` a porta, `ASSINA_ORIGIN` a origem exata. Ao mudar PORT, atualize também ASSINA_ORIGIN. Origem deve conter esquema + host + porta sem barra final. `ASSINA_MODE=homologacao` é obrigatório; outro valor encerra o processo. A origem padrão é http://127.0.0.1:8000; abrir localhost exige configurar explicitamente essa origem.

## Testar o fluxo
1. Criar conta e empresa com dados fictícios.
2. Novo documento → baixar PDF fictício → selecionar arquivo → cadastrar participantes → revisar.
3. No detalhe, emitir o link do participante, copiá-lo e abri-lo em outra aba. Nenhum e-mail é enviado.
4. Revisar PDF, aceitar termos e registrar nome autodeclarado fictício. Na ordem sequencial, concluir o participante anterior antes de abrir o seguinte.
5. Voltar ao detalhe, baixar artefato de homologação e evidências JSON. O PDF original permanece inalterado.

```bash
python3 tools/verify_evidence.py evidencias-homologacao.json --original original-teste.pdf --final homologacao-sem-icp.pdf
```

O verificador compara a cadeia e os arquivos fornecidos. Não prova completude, autoria, validade jurídica ou hora confiável. O exemplo em `examples/` foi produzido pela API com dados temporários inteiramente fictícios.

## Dados, backup e falhas
`runtime/` é criado com os dados e chaves locais e não deve ser versionado. Perder a chave torna os PDFs irrecuperáveis. Para um backup consistente de homologação, parar o processo e copiar o diretório inteiro para local protegido; para restaurar, parar, substituir o diretório e conferir hashes e trilha antes de retomar. Um backup/restauração automatizado e testado sob carga ainda é pendente. Não fazer cópia quente somente do arquivo SQLite.

Falhas na geração do PDF final revertem consumo e eventos da transação. Erros tratados removem o objeto final órfão; queda abrupta de processo pode exigir reconciliação de objetos. O wizard preserva rascunho se inclusão de participante ou disponibilização falhar; abra o detalhe para concluir. Não reenvia e-mail, não faz cobrança e não dispara webhook.

## Java (fronteira desabilitada)
Defina `SIGNER_INTERNAL_TOKEN` com ao menos 32 caracteres via ambiente seguro e execute:

```bash
java services/signer/src/main/java/br/com/assinabrasil/signer/SignerServer.java
```

Porta local padrão 9090 (`SIGNER_PORT`), somente 127.0.0.1. Todas as chamadas exigem `X-Internal-Token`. Health informa `signingEnabled=false` e `libraryLoaded=false`. As quatro operações retornam 501 sem interpretar o corpo. Não forneça certificado, senha ou chave privada a esse serviço. O perfil Maven `demoiselle` prepara dependências opcionais e não implementa a integração; Maven/artifacts e alvo Java 17 não foram executados nesta sessão.

## Logs
`run.py` desabilita access logs para não registrar URLs. O servidor não imprime tokens/PII em erros de validação. Proxy, APM, browser, extensões e infraestrutura externa precisam de revisão própria; não anexar corpos de requisições ou links de assinatura aos logs.
