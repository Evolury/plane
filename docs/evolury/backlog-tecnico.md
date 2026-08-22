# Backlog técnico

Dívida que **atravessa funcionalidades** e por isso não cabe no backlog de
nenhuma delas. Cada item traz o número medido, não a impressão.

Backlogs de funcionalidade ficam em [funcionalidades/](funcionalidades/); este
arquivo é para o que sobra.

## Em aberto

### A coluna do quadro não acompanha o valor de propriedade mudado em outra aba

Com o quadro agrupado por propriedade personalizada (ADR 0011), mudar o valor em
outra aba atualiza a **pastilha** do cartão na hora — o aviso de tempo real
`propriedade` revalida a leitura de valores do projeto (ADR 0013) —, mas o
cartão **não muda de coluna** até recarregar.

O motivo é onde a informação mora: a coluna vem do campo `property_<uuid>` que o
servidor anota em cada tarefa da resposta agrupada, e o aviso de tempo real não
carrega esse campo. São duas leituras do mesmo dado, e o aviso atualiza só uma.

**Número medido:** 1 caso — quadro agrupado por propriedade, com mais de uma aba
aberta. Não afeta quem move o cartão (essa aba reagrupa sozinha, otimista).

**Caminho provável:** o receptor do aviso `propriedade` conferir se o
agrupamento atual é de propriedade e, se for, rebuscar a página; ou o aviso
passar a carregar propriedade e opção, e o receptor gravar o campo anotado no
store — que é o que `updateIssueList` já sabe reagrupar.

### Ícones de e-mail hospedados no S3 de marketing do Plane

`apps/api/templates/emails/notifications/issue-updates.html` busca **doze
pictogramas** (estado, prioridade, responsável, etiqueta, prazo, duplicata,
bloqueio, vínculo, seta) em
`https://plane-marketing.s3.ap-south-1.amazonaws.com/plane-assets/emails/`.

Não são marca — são pictogramas funcionais —, e por isso ficaram de fora da
limpeza de 22/08/2026 ([1.38.0](../../CHANGELOG.md)). Mas são **dependência de
terceiro num e-mail nosso**: se o balde sair do ar, o e-mail de atualização de
tarefa chega quebrado, e enquanto ele estiver no ar entrega o IP de quem abre a
mensagem para a infraestrutura do Plane.

**Número medido:** 12 imagens em 1 modelo, dos 11 que existem. Os outros dez já
estão limpos.

**Caminho provável:** copiar os doze arquivos para `plane/static/logos/` — que
já hospeda os ícones sociais — e trocar o `src` por `{{ current_site }}/static/…`,
como `project_invitation.html` já faz. É substituição de atributo, sem mexer na
estrutura das tabelas.

**A guarda já cobre:** `plane/tests/unit/marca/test_marca_nos_emails.py` detecta
esses endereços e carrega o modelo numa exceção nomeada. Resolver a dívida é
apagar a entrada de `EXCECOES` e ver o teste passar.

### `plane.evolury.app.br` parado na 1.37.0

A produção de desenvolvimento não recebeu a 1.38.0, que está em
`app.qoowork.com.br`. Enquanto ficar atrás, ela **não tem o conserto do upload**
— mas ali o armazenamento é MinIO, que implementa POST assinado, então o defeito
não se manifesta. O que ela não tem é a marca corrigida nos e-mails e o proxy
com upstream nomeável.

**Número medido:** 1 versão de diferença (1.37.0 → 1.38.0), 4 PRs.

### Cloudflare em SSL _Full_, não _Full (strict)_

A zona `qoowork.com.br` está em **Full**: a Cloudflare valida que a origem fala
TLS, mas **não valida o certificado dela**. Com _Full (strict)_ passa a validar,
e o certificado de origem instalado já é da própria Cloudflare — ou seja, o
aperto não exige emissão nova.

Ficou em Full durante a subida para não confundir erro de certificado com erro
de aplicação. O site está provado desde 22/08/2026; não há mais razão para
segurar.

**Número medido:** 1 zona.

### A raiz `qoowork.com.br` redireciona para o app

Provisório por decisão de 22/08/2026: a raiz fica reservada para a página de
venda e assinatura, que será construída no Payload. Enquanto ela não existe,
raiz e `www` devolvem 301 para `app.qoowork.com.br`, para que ninguém que digite
o domínio caia em erro.

Quando a página entrar, o bloco da raiz no Caddy vira o dela e o redirecionamento
sai. O `EMAIL_FROM` **continua** em `@qoowork.com.br` — é no domínio raiz que o
DKIM está publicado e autenticado no Brevo, e movê-lo mandaria convite para spam.

### Cupom de valor fixo não existe no catálogo

`plane/utils/cupons.py` só conhece `percentual` (inteiro) e `cortesia`. Não há
como dizer "este cliente paga R$ 150" sem calcular porcentagem, e a porcentagem
inteira nem sempre chega ao valor desejado.

**Número medido:** apareceu em 22/08/2026, no teste real de pagamento. Sobre o
Essencial de R$ 290, os degraus vizinhos são 99% → R$ 2,90 (recusado: o Asaas
exige mínimo de R$ 5,00) e 98% → R$ 5,80. R$ 5,00 exigiria 98,27%.

**Caminho provável:** um terceiro tipo, `valor_fixo`, em que `Cupom.valor` é o
desconto em centavos. `valor_com_desconto` ganha um ramo; `fim_da_promocao` e
`primeira_cobranca` não mudam.

### O `AWS_S3_ENDPOINT_URL` do `planedev` aponta para o MinIO de outro projeto

A pilha de desenvolvimento usa `http://localhost:9000`, e nesta máquina quem
atende nessa porta é `evolury-minio` — de outro projeto. O MinIO do próprio
`planedev` **não publica porta no host**.

**Número medido:** descoberto em 22/08/2026 ao tentar provar o upload localmente.
A tentativa devolveu 403 por credencial errada. O 403 foi sorte: com credencial
compatível, o teste teria escrito no balde alheio.

**Caminho provável:** publicar a porta do `planedev-plane-minio-1` e apontar o
endpoint para ela, ou dar ao serviço um nome de host próprio.

### A configuração da instância não segue o ambiente

`manage.py configure_instance` usa `get_or_create`: ele **cria** as linhas de
`InstanceConfiguration` que faltam e **nunca atualiza** as que existem. Trocar
uma credencial no ambiente não muda nada em produção, porque o app lê do banco
(`SKIP_ENV_VAR=1`).

**Número medido:** mordeu **duas vezes** no mesmo dia, 22/08/2026 — a chave SMTP
do Brevo e a chave do Asaas rotacionada ficaram velhas no banco enquanto o
ambiente já tinha as novas. As duas foram corrigidas à mão, uma a uma.

**Caminho provável:** um `--sincronizar` no comando, que reescreve as linhas a
partir do ambiente quando divergirem, e diz quais mudou sem imprimir valor.

## Resolvido

### Migração nenhuma era executada por CI — 19/08/2026

O `pytest.ini` roda com `--nomigrations`: o banco de teste vem dos modelos, e as
migrações **nunca** eram executadas. Nenhum dos nove workflows subia banco ou
chamava `manage.py migrate`. **Vinte e quatro** migrações próprias entraram
assim — dependência errada, `RunPython` que quebra ou trava que conflita com
dado existente só apareceriam no deploy, em produção.

Apareceu de um jeito específico: uma injeção de defeito **dentro** de uma
migração não derrubou teste nenhum.

O workflow `Migrações` passou a subir Postgres e rodar dois passos:
`migrate --noinput` do zero, e `makemigrations --check --dry-run` para o inverso
— modelo alterado sem migração correspondente. Provado com defeito injetado, um
de cada vez: dependência apontando para migração inexistente e campo novo num
modelo derrubam a CI, cada um no seu passo.

### Diretório root do docker travava a troca de branch — 19/08/2026

`apps/api/plane/static-assets/collected-static` nasce do build da API,
pertence ao root e não estava em `.gitignore` nenhum. Vazio, não aparecia no
`git status` — mas o git tentava removê-lo ao trocar de branch, não conseguia, e
o `switch` falhava. Uma linha resolveu; conferido com o diretório presente, a
troca vai e volta.

### Rótulos do menu do editor - 19/08/2026

A contagem que eu tinha anotado ("38 literais") estava errada: os itens do editor
**já trazem** `i18n_name` ao lado do `name`, e o `name` é reserva. As 24 chaves
existiam e estavam traduzidas. O buraco era só nos pontos de render - a barra da
página lia o `name` direto. Corrigido, mais três literais de verdade ("Color",
"Full width", "Sticky toolbar").

### `no-use-before-define` - ligada em 19/08/2026

**A regra está ligada**, restrita a variáveis
(`{"functions": false, "classes": false, "variables": true}`) no `.oxlintrc.json`
— a forma que funciona; o `--rule-config` da linha de comando desliga a regra em
silêncio.

Das **180** ocorrências, **152 foram corrigidas de verdade**, em 53 arquivos, de
dois jeitos:

- **Arrow de escopo de módulo virou declaração de função.** Declaração é içada,
  então o uso antes da declaracao deixa de ser zona morta: o defeito some, não só
  o aviso. E o diff é de uma linha por símbolo, o que importa num fork que
  sincroniza com o upstream.
- **Declaração movida para antes do primeiro uso**, quando converter não cabia
  (componente em `observer`/`memo`, constante, genérico com anotação).

**As 28 restantes ficam congeladas pelo teto de avisos**, e é isso que impede a
volta do problema: uma ocorrência **nova** empurra a contagem acima do teto e
derruba a CI. Provado com defeito injetado.

Por que essas 28 não foram mexidas: são componentes referenciados no JSX de um
irmão (referência de renderização, nunca zona morta) e fechamentos locais cujo
uso está num `removeEventListener` de limpeza. Mover exigiria blocos grandes de
código herdado, e **três tentativas dessas eu tive de reverter**: o TypeScript
perde o estreitamento de tipo quando a função é içada para fora do `if` que a
protegia, e o movedor automático cortou errado em arquivos com genérico. O ganho
não paga o risco enquanto o teto segura a recorrência.

Quem reduzir esse número deve **baixar o teto junto**.

### Teto de avisos do lint que não segurava nada — 19/08/2026

O `apps/web` declarava `--max-warnings=11957` com **814 avisos reais**: cabiam
mais **11.143** antes de a CI reclamar. Os outros pacotes tinham folgas
parecidas (`apps/admin` 23/759, `apps/space` 56/676, `packages/propel` 59/3605).

É por isso que o aviso que denunciava o defeito da criação de página nunca
derrubou nada.

Todos os tetos passaram a ser o número real. Provado com defeito injetado: um
aviso novo em `apps/web` faz o `check:lint` sair com 1; removido, volta a 0.
Quem reduzir avisos deve **baixar o teto junto**, senão a folga volta.
