# ADR 0021 — Faturamento por assinatura, um espaço de cada vez

- **Status:** Aceito (21/08/2026)
- **Relacionado:** [ADR 0011](0011-propriedades-personalizadas.md) (teto de propriedades), [ADR 0012](0012-automacoes-personalizadas.md) (automações), [ADR 0020](0020-qoowork-nome-e-identidade.md) (QooWork), [ADR 0018](0018-exclusao-em-massa.md) (retenção e purga)

## Contexto

O QooWork tem clientes esperando para pagar e nenhuma peça de cobrança. O que
existe é o esqueleto: a tela de faturamento
([billing/root.tsx](../../../apps/web/core/components/workspace/billing/root.tsx))
diz "Community — tudo ilimitado" desde que a comparação de planos da nuvem do
Plane saiu, na v1.30.0.

Duas medições delimitam o trabalho:

```
grep -rl "feature_flag|featureFlag|FeatureFlag" apps/web apps/api packages  →  0 arquivos
```

Não existe motor de plano, direito ou flag. **Cada trava é um ponto novo.**

E os tetos que existem estão no lugar errado para vender: `TETO_DE_PROPRIEDADES = 30`
([issue_property.py:29](../../../apps/api/plane/db/models/issue_property.py#L29)) é
global e único; os tetos de automação que existem — profundidade 3, 20 subtarefas
por regra, execuções por hora — protegem o motor, não o plano. **Teto de regras
ativas não existe.**

O que existe e serve: `InstanceConfiguration` (chave/valor, com criptografia)
para os segredos; `InstanceWorkSpaceEndpoint` já entregando `total_members` e
`total_projects` paginados; o god-mode em [apps/admin](../../../apps/admin/app/routes.ts);
e o Celery com rotina diária às 00:00 UTC.

## Como o mercado faz

**Direito não é flag.** Flag serve para lançar recurso; direito modela plano,
limite, cortesia e exceção, e é avaliado **no servidor** a cada ação. São dois
tipos, e só dois: **booleano** (tem analytics ou não) e **quantidade** (5
propriedades, 3 assentos).

**Inadimplência.** A régua consolidada é tolerância de 3 a 7 dias, **degradar
antes de suspender** — somente leitura mantém o dado à vista e é motivo para
voltar —, suspensão entre o 7º e o 15º dia, aviso final entre o 20º e o 30º.
Réguas completas recuperam de 70% a 80% das falhas de pagamento, e o aviso
dentro do produto sozinho melhora a recuperação de 12% a 17%.

**Retenção pós-cancelamento.** 30, 60 ou 90 dias é o intervalo praticado; a
Microsoft mantém 90 dias em conta de função limitada, só para extração. A regra
que importa não é o número: é que a **exportação venha antes de tirar o
acesso**, não depois.

## Como o Asaas faz — e o que isso obriga

| Fato medido na documentação                                                                                | Consequência para o desenho                                                   |
| ---------------------------------------------------------------------------------------------------------- | ----------------------------------------------------------------------------- |
| Checkout com `chargeTypes: RECURRENT` só aceita `billingTypes: ["CREDIT_CARD"]`                            | PIX recorrente **não** passa pelo checkout hospedado                          |
| Assinatura com `billingType: PIX` gera cobrança a cada ciclo e o Asaas notifica por e-mail, SMS e WhatsApp | É o caminho do PIX na v1 — o cliente paga o QR todo ciclo                     |
| Pix Automático (Resolução BCB 422/2025) existe, é PJ e a liberação é gradual                               | Fica para depois da v1; resolve o esquecimento, não trava o lançamento        |
| **Não há webhook de assinatura para pagamento** — o que chega é `PAYMENT_*`, com o campo `subscription`    | O espelho de status é montado a partir de cobrança, nunca de assinatura       |
| No cartão, o Asaas tenta 5 vezes (3 no dia do vencimento, às 8h, 14h e 20h; mais 2 a cada 24h)             | Não construímos régua de retentativa. Construímos a régua de **consequência** |
| Entrega _at-least-once_; o `id` do evento é o que garante idempotência                                     | O `id` do evento é chave única no nosso banco                                 |
| 15 falhas consecutivas **interrompem a fila**; ao reativar, reenvia em ordem                               | O endpoint grava e responde 200 **sempre**; erro nosso nunca vira 500         |
| `authToken` do webhook tem de 32 a 255 caracteres                                                          | Segredo próprio, comparado em tempo constante                                 |
| Nota fiscal exige configuração municipal e agendamento                                                     | Emissão **manual pelo financeiro**, no painel do Asaas                        |

## A decisão

**1. A assinatura é do espaço de trabalho.** Um espaço, uma assinatura, um
responsável financeiro. Não há conta guarda-chuva nem limite de espaços por
cliente — quem quiser dois espaços assina dois.

**2. Três planos, e o do meio é o alvo.**

|                             | Essencial     | Profissional         | Avançado             |
| --------------------------- | ------------- | -------------------- | -------------------- |
| Assentos incluídos          | 3             | 10                   | 30                   |
| Mensal                      | **R$ 290**    | **R$ 690**           | **R$ 1.590**         |
| Por assento                 | R$ 96,67      | R$ 69,00             | R$ 53,00             |
| Assento adicional           | R$ 90         | R$ 65                | R$ 49                |
| Anual (2 meses grátis)      | R$ 2.900      | R$ 6.900             | R$ 15.900            |
| Assento adicional/ano       | R$ 900        | R$ 650               | R$ 490               |
| Convidados grátis           | —             | 2× os assentos pagos | 5× os assentos pagos |
| Propriedades personalizadas | 5 por projeto | 30 por projeto       | 30 por projeto       |
| Automações ativas           | 2             | sem teto             | sem teto             |
| Analytics                   | —             | ✓                    | ✓                    |
| Webhooks e API pública      | —             | ✓                    | ✓                    |

O preço do assento cai a cada nível — 96,67 → 69,00 → 53,00 — e o adicional cai
junto — 90 → 65 → 49. O adicional fica **abaixo** do assento do próprio plano
de propósito: a plataforma já está paga, o que entra é gente.

**Duas regras que viram teste automatizado**, porque tabela de preço incoerente
só aparece em reunião comercial:

1. `base(n) + adicional(n) × (incluídos(n+1) − incluídos(n)) > base(n+1)` —
   acumular excedente tem de custar mais que subir de plano.
   Medido: `290 + 90×7 = 920 > 690`; `690 + 65×20 = 1.990 > 1.590`.
2. Preço por assento e preço do adicional **caem** a cada nível.

O cruzamento é onde a régua empurra: com **8 pessoas** o Profissional já sai
mais barato que o Essencial esticado (R$ 690 contra R$ 740), e ainda traz
analytics, API, convidados, seis vezes mais propriedades e automação sem teto.
Com **24 pessoas**, o Avançado passa o Profissional esticado (R$ 1.590 contra
R$ 1.600).

**O Avançado vende escala, não funcionalidade.** Ele e o Profissional liberam os
mesmos recursos; o que muda é assento, preço por assento e cota de convidado.
É deliberado: espremer uma funcionalidade para dentro do plano maior só para
justificá-lo tiraria valor do plano do meio, que é o alvo.

**3. Assento tem três tipos, e só um paga.**

| Tipo                                 | Conta? | Regra                                                                                               |
| ------------------------------------ | ------ | --------------------------------------------------------------------------------------------------- |
| Membro (Admin ou Membro)             | Sim    | É o assento                                                                                         |
| Convidado (papel 5, acesso restrito) | Não    | Cota grátis por plano                                                                               |
| Robô (`is_bot`)                      | Nunca  | Já é excluído da contagem em [workspace.py](../../../apps/api/plane/license/api/views/workspace.py) |

Convidado grátis, e não cobrado à parte: ele é o canal pelo qual o cliente do
nosso cliente conhece a plataforma, e cobrá-lo criaria uma linha de cobrança
variável — com suporte e contestação — por receita marginal. A cota zero no
Essencial é o que dá ao convidado poder de venda.

**4. Integrações não entram no catálogo.** O que se vende de extensibilidade é
**webhook e API pública**, que são nossos e estão de pé. As integrações herdadas
com GitHub, GitLab e Slack não foram validadas neste fork, e vender por plano o
que não se verificou é dívida com o cliente, não receita.

**5. Direito é dado, não `if` espalhado.** Um catálogo declarativo em
`plane/utils/planos.py` e um único ponto de leitura em `plane/utils/direitos.py`,
com duas perguntas: `recurso_liberado(espaço, nome)` e `limite(espaço, nome)`.
A tela **esconde**; o servidor **recusa**, com `402 Payment Required` e código
próprio (`PLANO_NAO_INCLUI` 4801, `LIMITE_DO_PLANO` 4802). O 403 continua sendo
papel e permissão — separados, o cliente sabe qual tela mostrar sem adivinhar.

**6. Somente leitura é middleware, não permissão espalhada.** Quando o espaço
está restrito ou bloqueado, todo método que escreve é recusado num ponto só,
com lista curta e explícita de exceções: faturamento, exportação e autenticação.
É a mesma razão do [ADR 0008](0008-i18n-nos-pacotes-compartilhados.md) — _o que
é opcional não protege nada sozinho_: uma view criada daqui a seis meses estaria
descoberta se a trava dependesse de alguém lembrar de aplicá-la.

**7. A régua deriva de um campo só: `pago_ate`.**

| Estado           | Entra quando                             | O cliente pode                 |
| ---------------- | ---------------------------------------- | ------------------------------ |
| `sem_assinatura` | Espaço novo                              | Só contratar                   |
| `em_cortesia`    | Cupom de cortesia                        | Tudo, no plano do cupom        |
| `ativa`          | Pagamento confirmado                     | Tudo                           |
| `atrasada`       | D+0 do vencimento                        | **Tudo**, com aviso no produto |
| `restrita`       | D+7                                      | Ler e exportar                 |
| `bloqueada`      | D+15                                     | Faturamento e exportação       |
| `cancelada`      | Pedido do cliente                        | Tudo até `pago_ate`            |
| `encerrada`      | D+45, fim do ciclo cancelado, ou estorno | Nada; dados em retenção        |
| `removida`       | 90 dias depois de `encerrada`            | —                              |

`atrasada` não restringe nada porque o Asaas ainda está tentando o cartão:
restringir no D+0 puniria quem paga sozinho no D+1.

**A exportação sobrevive a todos os estados**, até a remoção. É o que transforma
bloqueio em algo defensável.

**Retenção de 90 dias**, com avisos em 30, 7 e 1 dia. É outro relógio que o
`HARD_DELETE_AFTER_DAYS = 60` do [ADR 0018](0018-exclusao-em-massa.md): aquele
purga item excluído; este encerra contrato.

**8. O Asaas é a autoridade do dinheiro; o nosso banco é a autoridade do
acesso.** A tela nunca pergunta ao Asaas se o cliente pagou — ela lê o espelho
local, alimentado por webhook e corrigido por conciliação diária. Indisponibilidade
do Asaas não bloqueia ninguém: sem evento, o estado simplesmente não muda.

**9. Idempotência pelo `id` do evento.** Todo evento é gravado antes de ser
processado, com o `id` do Asaas como chave única, e processado depois em fila
própria. O endpoint responde 200 mesmo quando o processamento falha, porque
devolver erro para o Asaas quinze vezes interrompe a fila dele — e aí a
integração fica muda sem ninguém saber. Quem descobre é o alarme: nenhum evento
em X horas com assinatura ativa acende o aviso no god-mode.

**10. Cupom e cortesia são o mesmo objeto, e toda promoção tem fim.** Dois
tipos: percentual (1 a 100%, por N ciclos ou permanente) e cortesia (N dias sem
cobrar). O Checkout do Asaas **não tem campo de cupom** — o desconto é aplicado
no `value` que enviamos, e uma rotina devolve o preço cheio quando a promoção
acaba (`PUT` na assinatura, `value` e `nextDueDate`). Sem essa rotina, um cupom
de 100% vira assinatura grátis para sempre, em silêncio.

**11. O preço é copiado na assinatura, não referenciado.** Reajustar a tabela
não pode reescrever o que o cliente contratou.

**12. O catálogo mora no código**, não no banco: são três planos que mudam raro,
e código é versionado, revisado e testável — sem tela de CRUD para manter.

**13. A nota fiscal fica inteira no Asaas, com emissão manual pelo financeiro.**
Nada de fiscal do lado do QooWork: nem cálculo, nem armazenamento, nem
exibição. O cliente vê a nota no Asaas. Automatizar a emissão é decisão de
depois da primeira validação do produto.

**14. Estorno encerra.** Reembolso é pedido por formulário no produto, o
financeiro processa no Asaas, e o evento `PAYMENT_REFUNDED` leva a assinatura
para `encerrada` na hora, entrando na retenção. Como o Asaas não bloqueia nada
por nós, o god-mode ganha **bloqueio manual** — o financeiro não depende de
webhook para cortar o acesso.

**15. Garantia de 30 dias, sem teste grátis aberto.** Quem entra, paga; quem se
arrepende em até 30 dias recebe de volta. O acesso de cortesia existe, mas por
cupom emitido pelo comercial — não por autoatendimento.

## Alternativas descartadas

**Campo `plano` no workspace.** Não guarda status, `pago_ate`, ids do Asaas,
preço contratado nem histórico. Viraria migração na primeira semana de cobrança
real.

**Catálogo de planos em banco, com CRUD.** Três planos que mudam uma vez por
ano não pagam uma tela de administração — e tirariam do código o único lugar
onde a coerência de preços pode ser testada.

**Bloquear o convite ao estourar o assento.** Atrito que gera suporte e não gera
receita. O assento extra entra no ciclo seguinte, e o convite avisa o valor e a
data.

**Pró-rata calculada pelo Asaas.** Ele não faz. No upgrade, a diferença
proporcional vira cobrança avulsa com link, e a assinatura passa a valer o preço
novo no ciclo seguinte. Downgrade só no próximo ciclo — senão rebaixar no dia 28
escaparia do excedente que já rodou.

**Cobrar convidado.** Ver decisão 3.

**Confiar no e-mail do QooWork para faturamento.** Toda comunicação de cobrança
sai pelo Asaas, que já entrega por e-mail, SMS e WhatsApp. A entrega de e-mail
transacional própria continua pendente de produção real, e o faturamento
deliberadamente não depende dela.

## Consequências

- **Uma migração** (0151) com cinco tabelas novas, todas em domínio nosso —
  nenhuma toca modelo do upstream.
- **`TETO_DE_PROPRIEDADES` deixa de ser constante e vira consulta ao plano.**
  O ponto de aplicação já existe; o valor passa a depender do espaço.
- **Teto de automações ativas é trava nova** — não existia.
- **Espaço novo nasce `sem_assinatura`; o que já existe entra em cortesia com
  prazo.** Aplicar `sem_assinatura` ao que está em produção congelaria cliente
  pagante no dia em que a trava fosse ligada. A migração dá 90 dias de cortesia
  a cada espaço existente — prazo, e não cortesia aberta, pelo mesmo motivo da
  decisão 10: cortesia sem data é assinatura grátis para sempre, em silêncio.
  Com data, ela aparece no painel com um relógio correndo, e o comercial tem
  esses 90 dias para classificar espaço por espaço.
- **O middleware de somente leitura atravessa toda a API.** É a peça capaz de
  quebrar o produto para quem está em dia — nasce desligada atrás de um estado
  que nenhum espaço tem ainda, e cada exceção dela é provada por injeção.
- **A API ganha um código de erro por trava** (faixa 4800), e o front ganha um
  store de plano lido uma vez por espaço.
- **Fora do código**: conta Asaas em produção com a configuração municipal da
  nota, webhook cadastrado com `authToken`, e o domínio `qoowork.com.br` de pé —
  a URL de retorno do checkout depende dele.
