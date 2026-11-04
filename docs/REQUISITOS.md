# Requisitos e aceite desta entrega

| Etapa solicitada | Entregue | Limite |
| --- | --- | --- |
| Interface e navegação | Landing e aplicativo em pt-BR; layout responsivo por CSS; estados vazios, busca, filtros, wizard, detalhes | Navegação visual desktop/mobile ainda não validada por indisponibilidade da prévia |
| Backend próprio | API executável, contas/sessões, empresas/memberships, RBAC, documentos, modelos, banco persistente e armazenamento privado | SQLite local; PostgreSQL/Supabase e RLS não integrados |
| Assinatura por link | Link temporário/revogável, PDF autorizado, consentimento versionado, intenção autodeclarada, auditoria, artefato PDF e JSON | Exclusivamente homologação; sem OTP, identidade verificada ou conclusão jurídica |
| Demoiselle Signer | Serviço Java separado, autenticação interna, quatro endpoints e contrato OpenAPI | Todas as operações criptográficas retornam 501; sem certificados, TSA, CRL/OCSP ou PAdES operacional |
| Versão comercial | Marca por tenant e quota de envelopes no backend | Sem planos comerciais definidos, cobrança, domínio ou publicação; API externa e webhooks apenas contratos |

## Fluxos disponíveis
- Cadastro cria usuário + primeira empresa em uma transação. Login, logout e troca de senha revogando sessões.
- Criação de outras empresas e seleção de memberships; marca e permissões por empresa.
- Upload de PDF fictício, inclusão/remoção de participantes no rascunho, disponibilização, emissão/revogação de links, cancelamento.
- Modelos de texto CRUD e geração de PDF fictício, para baixar e reenviar como documento.
- Signatários com busca, painel com contagens reais dos registros de teste e filtros de documentos.
- Exportação de evidências e verificação offline do original, artefato final e cadeia.

## Fora do entregue operacional
Recuperação por e-mail, verificação de e-mail, MFA, biometria, identificação por OTP, envio automático de convites, assinatura desenhada, posição de rubricas, vários arquivos por envelope, recusa do signatário, gestão de clientes/CRM independente, API keys comerciais, recebimento de pagamentos e entrega de webhooks. Não há números fictícios no dashboard. Uma pessoa em um signatário não vira usuário autenticado.
