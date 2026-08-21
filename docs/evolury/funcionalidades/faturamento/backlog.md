# Faturamento — backlog de implementação

- **Decisão:** [ADR 0021](../../decisoes/0021-faturamento-por-assinatura.md)
- **Especificação:** [especificacao.md](especificacao.md) · **Arquitetura:** [arquitetura.md](arquitetura.md)

Sete entregas empilhadas. Cada uma mescla sozinha e é verificável; juntas são a
v1. A ordem E1 → E2 → E3 → E4 é obrigatória — E5 e E6 dependem de E4, e E7 fecha.

Regra de todas: **nenhum teste fala com o Asaas**. A substituição acontece na
função de transporte, com respostas gravadas do sandbox.

## E1 — O domínio, sem tela e sem rede

- Migração `0151_evolury_faturamento`: `Assinatura`, `Cobranca`, `EventoAsaas`, `Cupom`, `HistoricoDeAssinatura`
- `utils/planos.py` — catálogo com os preços do ADR 0021
- `utils/regua.py` — máquina de estados a partir de `pago_ate`
- Códigos 4801–4806 em `error_codes.py`
- Todo espaço existente entra `sem_assinatura`; espaço novo nasce `sem_assinatura`

**Aceite**

1. Coerência do catálogo provada por teste: `290 + 90×7 > 690` e `690 + 65×20 > 1.590`
2. Descida monotônica de preço por assento e de adicional, provada por teste
3. A régua percorre os nove estados em teste unitário, dia a dia, sem banco
4. Preço do plano alterado sem alterar a régua **reprova** a suíte (injeção)

## E2 — O motor de travas

A maior e a mais arriscada. Sete travas booleanas e três quantitativas.

- `utils/direitos.py` com cache em Redis e invalidação
- `ExigePlanoCom(...)` em analytics, webhooks e API pública
- Limite quantitativo em propriedade, automação, convite de membro e de convidado
- `TETO_DE_PROPRIEDADES` deixa de ser constante única
- **Teto de automações ativas** — trava nova, não existia
- `SomenteLeituraMiddleware`, desligado atrás de estado que nenhum espaço tem
- `GET /workspaces/<slug>/plano/` e o store no front; a interface esconde o que o plano não inclui

**Aceite**

1. Cada uma das dez travas devolve 402 com o código certo, provada por teste de contrato
2. Cada trava, removida uma de cada vez, **reprova** a suíte
3. O middleware recusa escrita em espaço restrito e **deixa passar** faturamento, exportação e autenticação — as três exceções com teste próprio
4. Espaço `ativa` não sofre nenhuma restrição: uma tarefa é criada, editada e excluída com a suíte inteira verde
5. A tela não mostra botão que não funciona: o recurso fora do plano aparece com o rótulo do plano que o libera

## E3 — Asaas: cliente, webhook, conciliação

- `utils/asaas.py` com uma única função de transporte
- Configuração em `InstanceConfiguration` criptografada, ambiente sandbox/produção
- `POST /api/faturamento/asaas/webhook/` — token, grava, 200, enfileira
- `faturamento_evento`, `faturamento_conciliacao`, `faturamento_alarme`
- **Confirmar no sandbox**: checkout recorrente aceita PIX? A documentação diz que não

**Aceite**

1. Evento repetido não muda nada duas vezes (mesmo `asaas_event_id`)
2. Token errado → 401, e nada é gravado
3. Falha no processamento → 200 para o Asaas, `erro` e `tentativas` na tabela, reprocessável
4. Conciliação com divergência plantada corrige e registra o que corrigiu
5. Silêncio de X horas com assinatura ativa acende o alarme
6. Nenhuma chamada de rede na suíte — provado desligando o transporte

## E4 — Contratar

- Tela de faturamento de verdade: plano, uso contra teto, próxima cobrança, histórico
- Dados de cobrança com CPF/CNPJ — campo novo no produto
- Cartão: checkout do Asaas, retorno e liberação por `CHECKOUT_PAID`
- PIX: assinatura por API, link e QR na tela
- Cupom: percentual e cortesia, com validade e limite de usos
- Troca de plano: upgrade imediato com avulsa proporcional, downgrade no ciclo seguinte

**Aceite**

1. Assinar por cartão de ponta a ponta no sandbox, com o acesso liberado pelo evento — **não** pelo retorno do navegador
2. Assinar por PIX, pagar no sandbox, ver o estado virar `ativa`
3. Cupom de 100% por 30 dias libera o acesso e registra `promocao_termina_em`
4. Downgrade com o espaço acima do teto é recusado dizendo **o que** precisa sair
5. Excedente de assento aparece no valor do ciclo seguinte, e o convite avisa antes

## E5 — A régua na tela

- Faixa de aviso em `atrasada`, faixa fixa em `restrita`, tela cheia em `bloqueada`
- `faturamento_regua` diária
- Cancelar, reativar, exportar, pedir reembolso
- Avisos de remoção em 30, 7 e 1 dia

**Aceite**

1. Os cinco estados vistos no navegador contra o `planedev`, cache desligado e hash do chunk conferido
2. Exportar funciona em `bloqueada`
3. Cancelar mantém o acesso até `pago_ate`, e nem um dia a mais
4. Reativar dentro dos 90 dias recupera a mesma assinatura
5. `PAYMENT_REFUNDED` leva a `encerrada` na hora

## E6 — God-mode

- Rota `subscriptions` no admin, ao lado de Workspaces
- Lista com plano, status, `pago_ate`, uso contra teto, excedente, filtro por status
- Atribuir plano e cortesia à mão; **bloquear e desbloquear**
- Histórico por espaço; última sincronização com o Asaas

**Aceite**

1. O financeiro bloqueia um espaço sem `psql` e sem depender de webhook
2. Toda ação de god-mode grava `HistoricoDeAssinatura` com autor e motivo
3. A listagem devolve em uma consulta — sem N+1 sobre assinatura

## E7 — Fechar o ciclo comercial

- Excedente automático no valor do ciclo seguinte (`PUT` na assinatura)
- `faturamento_promocao`: preço cheio de volta, aviso 7 dias antes
- Agregados no god-mode: receita recorrente, distribuição por plano, inadimplência

**Aceite**

1. Espaço que passou do teto tem o valor do ciclo seguinte ajustado, e o histórico registra
2. Cupom vencido volta ao preço cheio — sem isso, 100% é grátis para sempre
3. Os agregados batem com uma contagem feita à mão em banco de teste

## Fora do código, e antes do primeiro cliente real

- Conta Asaas de produção com configuração municipal da nota fiscal
- Webhook cadastrado com `authToken` de 32 a 255 caracteres
- `qoowork.com.br` publicado — a URL de retorno do checkout depende dele
- Token do sandbox no `bws`
- Espaços existentes classificados um a um pelo comercial

## Deliberadamente fora da v1

- **Pix Automático** — entra quando a conta estiver elegível (PJ, liberação gradual)
- **Emissão automática de nota** — só depois da primeira validação do produto
- **Autoatendimento de teste grátis** — o comercial emite cupom
- **Integrações no catálogo** — não são vendidas por plano
- **Pró-rata no downgrade** — só no ciclo seguinte, e é decisão, não pendência
