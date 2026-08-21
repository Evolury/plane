# Faturamento — especificação

- **Decisão:** [ADR 0021](../../decisoes/0021-faturamento-por-assinatura.md)
- **Status:** aprovada (21/08/2026), implementação não iniciada

## O problema

O QooWork tem clientes esperando para pagar e nenhuma peça de cobrança. A tela
de faturamento diz "Community — tudo ilimitado", e é verdade: nenhum recurso
depende de plano nenhum.

## O que se vende

Uma assinatura por **espaço de trabalho**. Quem administra o espaço contrata,
troca, cancela e vê as cobranças; membro comum não vê a tela de faturamento.

|                                                           | Essencial | Profissional      | Avançado          |
| --------------------------------------------------------- | --------- | ----------------- | ----------------- |
| Assentos incluídos                                        | 3         | 10                | 30                |
| Mensal                                                    | R$ 290    | R$ 690            | R$ 1.590          |
| Assento adicional                                         | R$ 90     | R$ 65             | R$ 49             |
| Anual (2 meses grátis)                                    | R$ 2.900  | R$ 6.900          | R$ 15.900         |
| Assento adicional/ano                                     | R$ 900    | R$ 650            | R$ 490            |
| Convidados grátis                                         | —         | 2× assentos pagos | 5× assentos pagos |
| Propriedades personalizadas                               | 5/projeto | 30/projeto        | 30/projeto        |
| Automações ativas                                         | 2         | sem teto          | sem teto          |
| Analytics                                                 | —         | ✓                 | ✓                 |
| Webhooks e API pública                                    | —         | ✓                 | ✓                 |
| Tarefas, ciclos, módulos, visões, quadro/lista/calendário | ✓         | ✓                 | ✓                 |
| Minhas tarefas, Concluir, recorrentes, páginas pessoais   | ✓         | ✓                 | ✓                 |
| Tempo real, preenchimento e exclusão em massa             | ✓         | ✓                 | ✓                 |

**Assento** é membro (Admin ou Membro). **Convidado** não consome assento.
**Robô** (`is_bot`) nunca conta.

## Contratar

Duas portas, porque o Asaas impõe duas:

**Cartão** — o cliente escolhe plano e ciclo, confirma os dados de cobrança
(nome, CPF/CNPJ, e-mail, telefone) e vai para o **Checkout do Asaas**. Dado de
cartão nunca passa pelo QooWork. Ao voltar, a tela mostra "processando" até o
evento chegar; o acesso é liberado por `CHECKOUT_PAID`, não pelo retorno do
navegador — o retorno pode não acontecer.

**PIX** — a assinatura é criada por API com `billingType: PIX`. O Asaas gera a
cobrança do ciclo e **notifica o cliente por e-mail, SMS e WhatsApp**; a tela
do QooWork mostra o link e o QR da cobrança em aberto. O cliente paga a cada
ciclo; não há débito automático (Pix Automático fica para depois).

Em ambos, CPF ou CNPJ é obrigatório — é o que identifica o cliente no Asaas — e
o campo não existe hoje em lugar nenhum do produto.

## Cupom

Um código, dois tipos:

- **Percentual** — de 1% a 100%, por N ciclos ou permanente;
- **Cortesia** — N dias de acesso sem cobrança.

O comercial emite; o cliente digita na contratação ou na tela de faturamento.
Cupom tem validade, limite de usos e dono. **Toda promoção tem fim registrado**:
quando acaba, o preço cheio volta e o cliente é avisado com 7 dias de
antecedência.

Cupom de 100% por prazo é o "período de teste" — não existe teste grátis por
autoatendimento.

## Assentos, excedente e troca de plano

**Convidar nunca é bloqueado.** Passar do teto acrescenta assento adicional, e o
convite diz o valor e a data em que ele entra: **no próximo ciclo**, sem
proporcional.

**Convidado** também tem cota; ao estourá-la o convite de convidado é recusado,
com a mensagem dizendo qual plano a aumenta.

**Upgrade** vale na hora. A diferença proporcional do ciclo corrente vira uma
cobrança avulsa com link (PIX ou cartão), e a assinatura passa a valer o preço
novo no ciclo seguinte.

**Downgrade** só no próximo ciclo. Se o espaço estiver acima do teto do plano
menor, a tela diz exatamente o que precisa sair antes — quantos membros, quantos
convidados, quantas propriedades, quantas automações — e o pedido fica retido
até isso acontecer.

## Quando não pagam

| Dia        | Estado      | O que muda para quem usa                                                     |
| ---------- | ----------- | ---------------------------------------------------------------------------- |
| Vencimento | `atrasada`  | Nada muda. Faixa de aviso no topo, com o valor e o link                      |
| +7         | `restrita`  | **Somente leitura**: ver, filtrar, exportar. Não cria, não edita, não exclui |
| +15        | `bloqueada` | Toda navegação cai na tela de faturamento. Exportar continua                 |
| +45        | `encerrada` | Sem acesso. A assinatura é cancelada no Asaas                                |
| +135       | `removida`  | Dados apagados, 90 dias depois de encerrar                                   |

Os avisos de cobrança saem pelo **Asaas** (e-mail, SMS, WhatsApp). O QooWork
avisa **dentro do produto** — é o canal que o cliente inadimplente lê.

No cartão, o Asaas tenta cinco vezes antes do primeiro dia de atraso contar: três
no dia do vencimento (8h, 14h, 20h) e duas a cada 24h.

## Cancelar, reativar, ser reembolsado

**Cancelar** mantém o acesso até o fim do ciclo pago. Depois, `encerrada` e a
retenção de 90 dias começa.

**Reativar** recupera a mesma assinatura enquanto os dados existirem — dentro dos
90 dias. Passado esse prazo, é espaço novo.

**Garantia de 30 dias.** Um formulário no produto abre o pedido; o financeiro
processa o estorno no Asaas. Estorno **encerra o espaço na hora** e inicia a
retenção — não há reembolso com acesso mantido.

**Exportar funciona em todos os estados**, inclusive bloqueado, até a remoção.
Avisos de remoção em 30, 7 e 1 dia antes.

## As telas

**Espaço → Faturamento** (só administrador): plano e ciclo · uso contra o teto
(assentos, convidados, propriedades, automações) · próxima cobrança · trocar de
plano · aplicar cupom · dados de cobrança · histórico de cobranças com link do
Asaas · cancelar · pedir reembolso · exportar.

**Faixas de estado**: aviso em `atrasada`, faixa fixa em `restrita`, tela cheia
em `bloqueada`.

**Recurso fora do plano**: a tela não mostra botão que não funciona. Onde o
recurso é visível por natureza — uma aba, um menu —, ele aparece com o rótulo do
plano que o libera e leva à troca de plano. Nunca um erro genérico.

**God-mode → Assinaturas**: lista com plano, status, `pago_ate`, uso contra
teto e excedente · filtro por status · atribuir plano e cortesia à mão ·
**bloquear e desbloquear manualmente** · histórico por espaço · última
sincronização com o Asaas · agregados (receita recorrente, distribuição por
plano, inadimplência).

## Fronteiras declaradas

- **Nada de fiscal do lado do QooWork** — nem cálculo, nem armazenamento, nem
  exibição de nota. A emissão é manual, pelo financeiro, no painel do Asaas.
- **Nada de dado de cartão** — nem os quatro últimos dígitos.
- **Sem teste grátis por autoatendimento** — só cupom.
- **Sem Pix Automático na v1** — entra quando a conta estiver elegível.
- **Sem integrações no catálogo** — extensibilidade se vende como webhook e API.
- **Sem conta guarda-chuva** — dois espaços são duas assinaturas.
