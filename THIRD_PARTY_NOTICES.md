# Componentes externos e licenciamento

O pacote distribui código original e exemplos. Bibliotecas Python e Java são instaladas separadamente; não há dependências vendorizadas, JARs Demoiselle ou chaves privadas incluídas. O código original não é relicenciado sob a licença de uma biblioteca.

## Dependências diretas Python

| Componente | Versão fixada | Licença declarada nos metadados instalados |
| --- | --- | --- |
| FastAPI | 0.141.1 | MIT |
| Uvicorn | 0.52.1 | BSD-3-Clause |
| cryptography | 50.0.0 | Apache-2.0 OR BSD-3-Clause |
| pypdf | 6.10.0 | BSD-3-Clause |
| ReportLab | 4.4.9 | BSD; ver license.txt da distribuição |
| python-multipart | 0.0.32 | Apache-2.0 |
| HTTPX (testes) | 0.28.1 | BSD-3-Clause |

ReportLab fornece as fontes Bitstream Vera usadas na geração e incorporadas em subconjunto nos PDFs. Os arquivos TTF não estão redistribuídos neste pacote. Manter seus avisos ao redistribuir a biblioteca ou os arquivos de fonte. A lista completa de dependências transitivas e textos de licença deve ser gerada no ambiente de release; esta tabela não é um SBOM completo ou uma auditoria de licenças/vulnerabilidades.

## Demoiselle Signer - preparação de integração

Fonte oficial: https://github.com/demoiselle/signer
Documentação: https://www.frameworkdemoiselle.gov.br/v3/signer/
Versão preparada no POM opcional: 4.6.2.
Artefatos: `org.demoiselle.signer:policy-impl-pades`, `org.demoiselle.signer:chain-icp-brasil`.
Licença declarada pelo projeto: GNU LGPL v3.0; autoria atribuída pelo projeto ao SERPRO. Verificadas as fontes oficiais nesta sessão em 04/11/2026.

A biblioteca não foi baixada, modificada, vinculada ou usada para gerar os PDFs deste pacote. `SignerServer` é apenas fronteira de serviço que retorna 501, e `DemoiselleSignerAdapter` falha explicitamente. O perfil Maven opt-in não é uma implementação funcional de PAdES.

Antes de distribuir componente que incorpore Demoiselle, preservar autoria e avisos, incluir os textos oficiais de LGPL-3.0 e GPL-3.0 e avaliar entrega do código correspondente e condições de substituição/relink aplicáveis à combinação e suas modificações. Não adicionar restrições que removam direitos da biblioteca. A reserva proprietária do código original não se aplica aos componentes LGPL.

Fontes oficiais das licenças:
- https://www.gnu.org/licenses/lgpl-3.0.html
- https://www.gnu.org/licenses/gpl-3.0.html

Separar o serviço por HTTP é uma decisão de arquitetura que permite substituição do motor. Isso não é parecer jurídico nem garantia automática de cumprimento de licenças. A forma concreta de distribuição deve ser revisada antes do release, incluindo todas as dependências transitivas.
