# Contrato proposto para webhooks - NÃO operacional

Não há cadastro, fila, outbox, retries ou entrega de webhooks nesta versão. O helper `backend/webhooks.py` apenas assina/verifica bytes HMAC em testes, sem conexão ao fluxo de envelopes.

Proposta para implementação: outbox inserida na mesma transação do evento, identificador estável, payload versionado sem documentos nem links de assinatura, assinaturas HMAC-SHA256 com segredo por destino, timestamp e idempotência. Headers propostos: X-Assina-Event-Id, X-Assina-Timestamp (segundos Unix) e X-Assina-Signature (`v1=<hex>`). Mensagem assinada: `event_id + '.' + timestamp + '.' + bytes exatos do corpo` em UTF-8. Tolerância de relógio de 300 segundos no helper; o receptor ainda precisa persistir event-id para rejeitar replay dentro da janela.

Antes de conectar destinos, validar autorização do tenant, SSRF/DNS/IP privados, TLS, limites, rotação/revogação de segredo, retry/backoff, dead-letter, replay controlado e minimização de dados. Nada é enviado por este pacote.
