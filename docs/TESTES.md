# Validação executada em 04/11/2026

## Resultado
23 testes automatizados passaram na execução final: `python3 -m unittest discover -s tests -v` (11,528 segundos). O log integral está em `docs/test-results.txt`. O teste Java usa o JDK disponível em source-file mode, incluindo autenticação interna e recusa explícita de operações ICP-Brasil.

| Área | Evidência coberta |
| --- | --- |
| Contas | Sessão obrigatória, cookie HttpOnly, login inválido, CSRF/origem, troca de senha e invalidação de sessões |
| Empresas | Leitura/escrita cruzada recusadas para envelope, PDF, artefato, evidência e modelo; membership forjado sem acesso |
| RBAC | Viewer não escreve/configura nem eleva papel; admin não eleva a própria permissão |
| PDF/armazenamento | Tipo/magic bytes, rejeição de conteúdo JavaScript, limite de corpo, ausência de rota estática, arquivo cifrado |
| Links | Hash do token persistido, inválido, reemitido, revogado, expirado e envelope expirado |
| Consentimento | Ausente ou versão incorreta recusados; hash de documento diferente recusado; replay não duplica efeitos |
| Ordem/estados | Sequência imposta pelo servidor, rascunho/disponibilização/cancelamento e revogação |
| Integridade | Original adulterado bloqueia confirmação sem consumo; artefato alterado não pode ser baixado |
| Concorrência | Duas confirmações simultâneas do mesmo token produzem uma confirmação e um artefato; outra é recusada |
| Falha de finalização | Falha injetada na geração do PDF reverte status, evento e consumo; nova tentativa pode concluir |
| Auditoria | Triggers bloqueiam update/delete; cadeia adulterada ou com começo removido é rejeitada |
| Manifesto offline | Arquivos e compromissos do manifesto são comparados; alteração de nome/termos/hash final é rejeitada |
| Funcionalidades | Marca, várias empresas, modelos CRUD/PDF e exclusão/adição de participantes no rascunho |
| Fronteiras | API ICP retorna 501, recuperação 503, cobrança desabilitada; Java sem auth 401, operações 501 |
| Webhook helper | HMAC cobre id/tempo/corpo e rejeita divergência/janela expirada; entrega não implementada |

## Outras verificações
- `python3 -m compileall -q backend tools`: passou.
- `node --check web/app.js`: passou (sintaxe, não execução DOM).
- Java compilado com `java -m jdk.compiler/com.sun.tools.javac.Main`; serviço testado com OpenJDK 21. Alvo de compilação Java 17 e perfil Maven Demoiselle não foram validados.
- Exemplo produzido por chamadas reais à API em diretório temporário, sem dados reais; verificador offline aprovou original + PDF final + JSON.
- As duas páginas do PDF final de exemplo foram renderizadas com Poppler e inspecionadas visualmente. Fontes do relatório são incorporadas; marca de homologação e ressalvas estão visíveis.
- OpenAPI exportado da aplicação real em `contracts/platform.openapi.json`.
- `requirements.lock` registra 24 distribuições presentes no ambiente Python 3.12 validado, sem empacotar wheels. Instalação limpa pela rede não foi executada.

## Não validado
A prévia gerenciada retornou `preview relay unavailable: No such file or directory` tanto no início quanto no diagnóstico. Não foi possível abrir este aplicativo no navegador. Desktop/mobile, envio de formulários no DOM, acessibilidade, comportamento do visualizador PDF e clipboard permanecem sem validação interativa. CSS responsivo implementado não equivale a responsividade visual comprovada.

Não houve teste de carga, pentest, antimalware/sandbox, OTP/MFA, PostgreSQL/RLS, storage/KMS gerenciado, restauração sob falha, produção/HTTPS de domínio, cobrança, SMTP/webhooks, conformidade jurídica ou interoperabilidade ICP-Brasil. Hashes e testes locais não substituem essas validações.

O runtime emitiu aviso de depreciação de Starlette TestClient com HTTPX. Os testes passaram com as versões fixadas; revisar o transporte de testes quando atualizar dependências. A interface React remota permanece sem build corrigido nesta sessão por falta de créditos do Lovable.
