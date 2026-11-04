# Próximas entregas após 0.2.0

## Etapa 1 - integrar o código existente
Resolver créditos ou obter repositório editável do Lovable; corrigir o build observado; decidir interface única; conectar os serviços ao contrato real da API; validar visualmente desktop/mobile, acessibilidade e fluxo em browser.

## Etapa 2 - infraestrutura de homologação compartilhada
PostgreSQL com migrations/RLS e teste de tenant, object storage privado/KMS, scanner de PDF isolado, TLS/reverse proxy, SMTP verificado, recuperação de conta, MFA e OTP de participante. Backups e restauração sob falha; limites e monitoramento.

## Etapa 3 - identidade e evidências operacionais
Escolher fatores de identidade, termos e bases legais, retenção, âncora externa/WORM e autoridade de tempo. Revisar integridade com documentos complexos, documentos assinados e validador independente. Não converter o nome autodeclarado do teste em identidade verificada.

## Etapa 4 - motor ICP-Brasil
Escolher A1/A3/remoto, implementar e validar a biblioteca Demoiselle no serviço separado. Validar cadeia, políticas de assinatura, revogação CRL/OCSP, TSA, LTV e interoperabilidade PAdES. Configurar credenciais somente em cofre/servidor apropriado. Revisar distribuição e licenças.

## Etapa 5 - comercial
Definir planos e domínio; gateway, checkout, conciliação, quotas/entitlements, API keys com escopos e outbox/webhooks. Testar cobranças idempotentes, cancelamento, downgrade, retries e isolamento. Só publicar após critérios de segurança, integridade, auditoria e validação jurídica aprovados.
