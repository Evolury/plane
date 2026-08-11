# Política de segurança

Este documento descreve como reportar vulnerabilidades neste produto. A
segurança das instâncias que operamos é prioridade, e o trabalho de quem
identifica e reporta problemas é parte disso.

## Reportando uma vulnerabilidade

Envie os achados para [contato@evolury.com.br](mailto:contato@evolury.com.br).
Inclua tudo o que for necessário para reproduzir e avaliar o problema, com o IP
ou a URL do sistema afetado.

Para que a divulgação seja responsável e efetiva:

- Mantenha a confidencialidade e não divulgue publicamente a vulnerabilidade
  antes de termos tido a oportunidade de investigar e corrigir.
- Não rode varreduras automatizadas contra a nossa infraestrutura sem
  autorização prévia. Se precisar, fale conosco para montarmos um ambiente de
  testes.
- Não explore a vulnerabilidade para fins maliciosos, como acessar ou alterar
  dados de usuários.
- Não use ataques físicos, engenharia social, negação de serviço (DDoS), spam ou
  ataques a aplicações de terceiros como parte do teste.

## Fora de escopo

- Vulnerabilidades que exijam ataque man-in-the-middle ou acesso físico ao
  dispositivo do usuário.
- Content spoofing ou injeção de texto sem vetor de ataque claro ou sem
  capacidade de modificar HTML/CSS.
- Questões relacionadas a spoofing de e-mail.
- Ausência de DNSSEC, CAA ou cabeçalhos CSP.
- Ausência das flags secure ou HTTP-only em cookies não sensíveis.

## Nosso compromisso

- **Tempo de resposta** — confirmamos o recebimento em até três dias úteis, com
  uma estimativa de prazo para resolução.
- **Proteção legal** — não tomaremos medidas legais contra quem reportar
  vulnerabilidades seguindo estas diretrizes.
- **Confidencialidade** — o relato é tratado com sigilo; não divulgamos dados
  pessoais de quem reporta sem consentimento.
- **Reconhecimento** — com sua permissão, temos prazer em reconhecer
  publicamente a contribuição depois que o problema for resolvido.
- **Resolução** — acompanhamos o processo até o fim, com atualizações ao longo
  do caminho, e coordenamos a divulgação responsável quando estiver corrigido.

## Vulnerabilidades no upstream

Este produto deriva do Plane Community Edition (ver [UPSTREAM.md](UPSTREAM.md)).
Vulnerabilidades que existam também no código do upstream devem ser reportadas
**a nós**, não à Plane Software — nós avaliamos e, quando for o caso, coordenamos
a comunicação com o projeto de origem.
