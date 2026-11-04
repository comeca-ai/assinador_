# Segurança, privacidade e bloqueadores

Esta versão é exclusiva de homologação local e não foi auditada externamente. Testes automatizados cobrem comportamentos específicos; não demonstram segurança integral, validade jurídica ou conformidade LGPD.

## Controles implementados
- Senhas scrypt (N=32768, r=8, p=1), salt CSPRNG de 16 bytes; senha de 12 a 128 caracteres.
- Cookie HttpOnly, SameSite=Strict, Secure quando a origem configurada é HTTPS; sessão de 8 horas, revogável e armazenada por hash.
- Origem exata obrigatória para mutações, CSRF vinculado à sessão, Content-Type esperado, TrustedHost e nenhuma política CORS permissiva.
- Headers CSP sem scripts inline externos, nosniff, referrer no-referrer, cache no-store e restrição de câmera/microfone/geolocalização. HSTS apenas em HTTPS.
- Autorização/membership em cada recurso; queries parametrizadas; FKs compostas de tenant. Acesso a documentos é corporativo, não privado por usuário.
- Rate limit SQLite por origem de rede derivada de HMAC: 20 requisições de auth/min e 100 públicas/min por IP observado, sem confiar em X-Forwarded-For. Não substitui WAF distribuído; remover rate limits antigos é uma tarefa operacional pendente.
- Tokens aleatórios de 256 bits, persistidos por SHA-256; revogação, expiração, consumo transacional e ausência em query string. URLs completas são mostradas uma vez ao emissor; trate-as como segredos.
- PDF com limite de requisição/arquivo, magic bytes, parser e rejeição conservadora de criptografia, formulários, anotações e construções ativas. Arquivos rejeitados não são armazenados.
- Objetos privados AES-256-GCM com nonce aleatório e AAD vinculada ao caminho; criação exclusiva e nomes gerados pelo servidor. Hash revalidado antes de leitura, disponibilização e confirmação.
- Auditoria append-only com triggers e hash chain; o administrador do banco ainda pode remover triggers ou reescrever tudo. Não é WORM, assinatura de log ou âncora externa.

## Limites importantes
O parser PDF roda no processo da API, sem sandbox de CPU/memória ou antimalware. Arquivos complexos ou comprimidos podem consumir recursos antes da validação. Não processe documentos reais ou PDFs não confiáveis nesta versão. A checagem estrutural não garante sanitização.

A chave de objetos fica em `runtime/objects/storage.key` com permissão 0600. Os arquivos e chave no mesmo volume dependem da proteção do host. O SQLite contém metadados pessoais sem criptografia própria em repouso. Não há KMS, rotação de chave, cofre, segregação de backups ou política de retenção automatizada.

A posse do link e nome autodeclarado não demonstram identidade. Não são implementados certificado digital, validação ICP-Brasil, CRL/OCSP, LTV ou autoridade de carimbo do tempo. Os horários vêm do relógio do servidor, sem autoridade externa.

Cadastro não verifica e-mail. Há risco de registro de endereço de terceiro, abuso de contas e tentativas distribuídas. Não expor o servidor local na Internet; antes disso adicionar verificação de identidade, recuperação de conta segura e MFA de administradores. HTTP é permitido somente para loopback. Proxy reverso precisa de configuração e testes próprios.

## Dados e transparência
Persistem nome e e-mail de contas/participantes, nome autodeclarado, empresas, PDFs, hash/versão de termos, horários e IDs. Eventos evitam e-mail e nome em claro, usando IDs e digest quando possível. Não se coleta CPF, biometria ou geolocalização. Não são declarados IP ou user-agent como evidência; a chave HMAC de rede serve apenas ao rate limit.

Consentimento da interface é versão de teste, não um aviso de privacidade comercial nem definição de base legal LGPD. Antes do uso real, o responsável deve definir finalidade, base legal, retenção, direitos dos titulares, operadores, resposta a incidentes e contratos. Não há endpoint de exclusão/retificação ou retenção implementado; precisa ser conciliado com obrigações de evidência. Manifestos de auditoria podem revelar IDs de outros envelopes da mesma empresa, pois exportam a cadeia corporativa completa.

## Validações de lançamento pendentes
Revisão jurídica brasileira, pentest independente, ameaça/abuso, isolamento em PostgreSQL/RLS, validação de armazenamento gerenciado, restauração completa sob falha, testes de carga/recursos, monitoramento e resposta a incidentes, identidade dos signatários, imutabilidade/âncora externa e interoperabilidade documental. Produção não autorizada por esta entrega.
