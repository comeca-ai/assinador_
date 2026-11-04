# Retomada no projeto existente

Projeto: https://lovable.dev/projects/707da202-a3f6-4baf-974a-0ae112895b9e
Commit inicial inspecionado: `8a90219a29c7497a3ffc707967c4ab6e250b8f80`.

## Constatação
Foram lidos AGENTS.md, package.json, rotas/layouts, routeTree e serviços. A geração criou telas React/TanStack, tipos e dados em memória. A própria resposta final do Lovable declarou build quebrado, sem identificar a causa, e ausência de teste de navegação. A tentativa de continuar recebeu erro de workspace sem créditos. Não se atribui o erro a um arquivo específico sem diagnóstico.

Foi habilitado o banco Supabase pelo conector, sem aplicar DDL ou seed. Isso não conecta os mocks ao banco e não implementa autenticação do projeto remoto. Nenhum deploy foi solicitado ou executado.

## O que este pacote faz
Frontend independente e API Python/SQLite executáveis juntos, com fluxos reais de homologação. Não replica o React original nem altera sua história Git. O nome segue configurável por empresa, preservando a decisão futura de marca.

## Caminhos concretos para integração
1. Quando os créditos estiverem disponíveis ou houver checkout/repositório conectado, obter o código remoto, executar o build e corrigir o erro observado sem force push.
2. Escolher a interface: preservar React e substituir serviços de memória por acesso à API, ou portar este frontend buildless. Não misturar dois fluxos de assinatura como se fossem um backend único.
3. Hospedar a API atrás da mesma origem da interface. O contrato real está em `contracts/platform.openapi.json`; `contracts/lovable-api-client.ts` é ponto de partida, não integração já ligada. Para upload usar FormData, sem Content-Type manual. Não colocar sessão em localStorage.
4. Migrar SQLite para PostgreSQL com driver, migrations versionadas, RLS, grants mínimos e isolamento testado com duas contas. Não reutilizar senha/sessões antigas de teste como produção. O Supabase habilitado está vazio em relação a esta entrega.
5. Conectar storage privado gerenciado e SMTP/OTP, depois executar novamente o fluxo inteiro, incluindo falhas e revogação. Preservar avisos de homologação até completar validações.
6. Somente depois das validações documentais/operacionais/jurídicas, definir marca definitiva, domínio, planos e autorização de publicação.

Não é necessário decidir a marca definitiva para testar o pacote. Crédito ou acesso a um repositório editável é necessário para aplicar alterações no projeto Lovable; o pacote entregue pode ser executado e evoluído independentemente.
