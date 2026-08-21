# Faturamento — arquitetura

- **Decisão:** [ADR 0021](../../decisoes/0021-faturamento-por-assinatura.md)
- **Especificação:** [especificacao.md](especificacao.md)

## Onde o domínio mora

Domínio inteiramente nosso: nenhum modelo do upstream é alterado, e os pontos de
contato com arquivo herdado são poucos e listados no fim.

```
apps/api/plane/
├── db/models/faturamento.py            Assinatura, Cobranca, EventoAsaas, Cupom, HistoricoDeAssinatura
├── db/migrations/0151_evolury_faturamento.py
├── utils/planos.py                     catálogo declarativo + regras de coerência
├── utils/direitos.py                   recurso_liberado(), limite(), uso()
├── utils/regua.py                      máquina de estados a partir de pago_ate
├── utils/asaas.py                      cliente fino: UMA função de transporte
├── middleware/somente_leitura.py       recusa escrita em espaço restrito/bloqueado
├── app/views/faturamento/              assinatura, cupom, checkout, webhook, reembolso
├── app/urls/faturamento.py
├── bgtasks/faturamento_evento.py       processa EventoAsaas
├── bgtasks/faturamento_regua.py        avança estados (diária)
├── bgtasks/faturamento_conciliacao.py  compara espelho × Asaas (diária)
└── license/api/views/assinatura.py     god-mode
```

No front: `apps/web/core/store/faturamento/`, `apps/web/core/components/workspace/billing/`
e a rota nova `subscriptions` em [apps/admin](../../../../apps/admin/app/routes.ts).

## Modelo de dados

**`Assinatura`** — uma por espaço (`workspace` único).

| Campo                                                             | Por quê                                                        |
| ----------------------------------------------------------------- | -------------------------------------------------------------- |
| `plano`, `ciclo`                                                  | O que foi contratado                                           |
| `status`                                                          | Um dos nove estados da régua                                   |
| **`pago_ate`**                                                    | O relógio de onde toda a régua deriva                          |
| `proxima_cobranca_em`                                             | O que a tela mostra                                            |
| `assentos_incluidos`, `valor_base`, `valor_por_assento`           | **Cópia** do catálogo no ato — reajuste não reescreve contrato |
| `assentos_extras`                                                 | Cobrados no ciclo corrente                                     |
| `asaas_customer_id`, `asaas_subscription_id`, `asaas_checkout_id` | O vínculo                                                      |
| `cupom`, `promocao_termina_em`                                    | Toda promoção tem fim                                          |
| `cancelada_em`, `encerrada_em`, `remover_dados_em`                | Cancelamento e retenção                                        |

O caminho de volta usa `externalReference` com o id do espaço, para que um
evento órfão ainda encontre dono.

**`Cobranca`** — espelho de cada `payment`: `asaas_payment_id` (único), `status`,
`valor`, `vencimento`, `pago_em`, `link`, `forma`. É o histórico que a tela mostra.

**`EventoAsaas`** — `asaas_event_id` **único**, `tipo`, `payload`, `recebido_em`,
`processado_em`, `tentativas`, `erro`. A unicidade é o que impede a dupla
contagem; o `payload` cru é o que permite reprocessar sem pedir nada ao Asaas.

**`Cupom`** — `codigo` (único), `tipo`, `valor`, `validade`, `usos_max`, `usos`,
`criado_por`.

**`HistoricoDeAssinatura`** — quem mudou o quê, quando e por quê. Toda mudança
de plano, estado ou cortesia passa por aqui, inclusive as feitas no god-mode.

## O motor de direitos

`plane/utils/planos.py` é declarativo e é a única fonte de números:

```python
PLANOS = {
    "essencial": Plano(
        assentos=3, mensal=29000, anual=290000, adicional_mensal=9000,
        convidados_por_assento=0,
        recursos={"analytics": False, "api_publica": False, "webhooks": False},
        limites={"propriedades_por_projeto": 5, "automacoes_ativas": 2},
    ),
    ...
}
```

Valores em centavos, inteiros — dinheiro não é ponto flutuante.

Dois testes guardam o catálogo, e são a razão de ele viver em código:

1. **Coerência da régua**: `base(n) + adicional(n) × (incluídos(n+1) − incluídos(n)) > base(n+1)`;
2. **Descida monotônica**: preço por assento e preço do adicional caem a cada nível.

`plane/utils/direitos.py` responde duas perguntas e nada mais:

```python
recurso_liberado(workspace_id, "analytics") -> bool
limite(workspace_id, "propriedades_por_projeto") -> int | None
uso(workspace_id, "assentos") -> int
```

Cache em Redis com TTL curto, invalidado na troca de plano e no webhook. É
caminho quente: a checagem entra em criação de tarefa e em convite.

**Aplicação:**

- Recurso booleano: permission class `ExigePlanoCom("analytics")` na view;
- Limite quantitativo: checagem explícita antes da escrita — propriedade, automação, convite, convidado;
- Resposta: `402 Payment Required` com `{"error_code": 4801, "recurso": ..., "plano_atual": ..., "planos_com": [...]}`.

Códigos novos em [error_codes.py](../../../../apps/api/plane/utils/error_codes.py),
faixa 4800: `PLANO_NAO_INCLUI` 4801, `LIMITE_DO_PLANO` 4802,
`ESPACO_SOMENTE_LEITURA` 4803, `ESPACO_BLOQUEADO` 4804, `CUPOM_INVALIDO` 4805,
`SEM_ASSINATURA` 4806.

## Somente leitura

`plane.middleware.somente_leitura.SomenteLeituraMiddleware`, acrescentado ao fim
da lista em [common.py:117](../../../../apps/api/plane/settings/common.py#L117),
depois da autenticação — ele precisa saber quem é o usuário.

Regra: método fora de `GET`, `HEAD`, `OPTIONS` em rota de espaço cujo status seja
`restrita` ou `bloqueada` → 402 com `ESPACO_SOMENTE_LEITURA`. O espaço sai do
caminho da URL (`/api/workspaces/<slug>/...`), com cache do par slug → status.

Exceções, curtas e explícitas: rotas de faturamento, exportação, autenticação e
`/api/instances/`. `bloqueada` mantém as mesmas exceções — a diferença dela é de
tela, não de API.

É a peça capaz de quebrar o produto para quem está em dia. Nasce atrás de um
estado que nenhum espaço tem, e cada exceção é provada por injeção.

## Integração com o Asaas

`plane/utils/asaas.py` expõe uma única função de transporte — `_requisitar(metodo, caminho, corpo)` —
e funções finas por operação: `criar_cliente`, `criar_checkout`, `criar_assinatura`,
`atualizar_assinatura`, `cancelar_assinatura`, `criar_cobranca_avulsa`,
`buscar_assinatura`, `listar_cobrancas`. **Nenhum teste chama a rede**: a
substituição acontece na função de transporte, com respostas gravadas do sandbox.

Configuração em `InstanceConfiguration` criptografada, categoria `faturamento`:
`ASAAS_API_KEY`, `ASAAS_WEBHOOK_TOKEN`, `ASAAS_AMBIENTE` (`sandbox` ou
`producao`). A base muda com o ambiente: `https://api-sandbox.asaas.com/v3` ou
`https://api.asaas.com/v3`.

**Contratação por cartão**: `POST /checkouts` com `chargeTypes: ["RECURRENT"]`,
`billingTypes: ["CREDIT_CARD"]`, `subscription.cycle`, `subscription.nextDueDate`,
`callback.successUrl`, `externalReference` = id do espaço. Guardamos o `id` e
redirecionamos para o `link`.

**Contratação por PIX**: `POST /customers` (se ainda não houver) e
`POST /subscriptions` com `billingType: "PIX"`. O Asaas gera a cobrança e
notifica.

**Troca de plano**: `PUT /subscriptions/{id}` com `value` e `nextDueDate`. A
diferença proporcional do upgrade vai como cobrança avulsa (`POST /payments`,
`billingType` do cliente). `updatePendingPayments` fica **falso**: cobrança já
gerada não muda de valor no meio do caminho.

**Estorno**: o financeiro processa no painel; nós reagimos ao evento. O endpoint
`POST /payments/{id}/refund` fica disponível no cliente, mas não é chamado pela
aplicação na v1.

## Webhook

`POST /api/faturamento/asaas/webhook/` — público, sem sessão.

1. Compara o header `asaas-access-token` com `ASAAS_WEBHOOK_TOKEN` em tempo constante;
2. Grava `EventoAsaas` (`asaas_event_id` único — evento repetido é ignorado aqui);
3. Responde **200**, sempre;
4. Enfileira `faturamento_evento`.

O passo 3 é decisão de projeto: quinze respostas de erro interrompem a fila do
Asaas, e a integração fica muda. Erro de processamento vira `tentativas` e
`erro` na nossa tabela, com nova tentativa em fila própria.

Eventos assinados: `CHECKOUT_PAID`, `PAYMENT_CREATED`, `PAYMENT_CONFIRMED`,
`PAYMENT_RECEIVED`, `PAYMENT_OVERDUE`, `PAYMENT_REFUNDED`,
`PAYMENT_PARTIALLY_REFUNDED`, `PAYMENT_DELETED`, `SUBSCRIPTION_UPDATED`,
`SUBSCRIPTION_INACTIVATED`, `SUBSCRIPTION_DELETED`.

Como **não existe webhook de assinatura para pagamento**, o estado é montado a
partir da cobrança: o campo `subscription` do payload é o que liga o evento à
`Assinatura`; `externalReference` é o caminho reserva.

## Rotinas

| Tarefa                    | Quando            | O que faz                                                                                        |
| ------------------------- | ----------------- | ------------------------------------------------------------------------------------------------ |
| `faturamento_evento`      | Por evento        | Aplica o efeito e invalida o cache de direitos                                                   |
| `faturamento_regua`       | Diária, 00:30 UTC | Avança `atrasada` → `restrita` → `bloqueada` → `encerrada` → `removida`                          |
| `faturamento_conciliacao` | Diária, 01:15 UTC | Compara espelho × Asaas (status, `nextDueDate`, `value`, cobranças recentes), corrige e registra |
| `faturamento_promocao`    | Diária            | Devolve o preço cheio quando a promoção acaba; avisa 7 dias antes                                |
| `faturamento_alarme`      | De hora em hora   | Nenhum evento em X horas com assinatura ativa → aviso no god-mode                                |

O alarme existe porque a fila interrompida do Asaas é silenciosa: sem ele,
quem descobre é o cliente.

## Front

`GET /api/workspaces/<slug>/plano/` devolve, numa chamada, plano, ciclo, status,
`pago_ate`, limites, uso e o que está liberado. Um store por espaço alimenta:

- os cadeados da interface (esconder, nunca desabilitar em silêncio);
- as faixas de estado;
- a tela de faturamento e a de troca de plano.

A tela esconde; **o servidor recusa**. Nenhuma trava existe só no cliente.

## Pontos de contato com o upstream

| Arquivo herdado                                                                                                              | Mudança                                             |
| ---------------------------------------------------------------------------------------------------------------------------- | --------------------------------------------------- |
| [settings/common.py](../../../../apps/api/plane/settings/common.py)                                                          | Um middleware na lista                              |
| [db/models/issue_property.py](../../../../apps/api/plane/db/models/issue_property.py)                                        | `TETO_DE_PROPRIEDADES` deixa de ser constante única |
| [views/project/issue_property.py](../../../../apps/api/plane/app/views/project/issue_property.py)                            | O teto passa a vir do plano                         |
| [views/workspace/invite.py](../../../../apps/api/plane/app/views/workspace/invite.py)                                        | Conta assento e convidado antes de convidar         |
| [views/analytic/](../../../../apps/api/plane/app/views/analytic/)                                                            | Permission de plano                                 |
| [views/webhook/](../../../../apps/api/plane/app/views/webhook/), [views/api.py](../../../../apps/api/plane/app/views/api.py) | Permission de plano                                 |
| [utils/error_codes.py](../../../../apps/api/plane/utils/error_codes.py)                                                      | Faixa 4800                                          |
| [license/api/views/workspace.py](../../../../apps/api/plane/license/api/views/workspace.py)                                  | Junta a assinatura à listagem do god-mode           |
| [components/workspace/billing/root.tsx](../../../../apps/web/core/components/workspace/billing/root.tsx)                     | Deixa de ser esqueleto                              |

Cada um recebe o comentário `Evolury:` apontando o porquê, como manda o
[README](../../README.md).
