# ADR 0015 — Páginas pessoais em "Minhas tarefas", compartilhadas por pessoa

- **Status:** Aceito (19/08/2026)
- **Contexto:** funcionalidade [paginas-pessoais](../funcionalidades/paginas-pessoais/especificacao.md)
- **Relacionado:** [ADR 0001](0001-minhas-tarefas-overlay-pessoal.md) (overlay pessoal), [ADR 0004](0004-idioma-unico-pt-br.md) (idioma), [ADR 0013](0013-atualizacao-em-tempo-real.md) (o `live` que edita a página)

## Contexto

Página só existia dentro de projeto. Quem trabalha por "Minhas tarefas" — que é
um espaço pessoal atravessando projetos — não tinha onde escrever: nota de
reunião, rascunho, checklist que ainda não pertence a projeto nenhum. Escolher um
projeto só para ter onde escrever é uma decisão que a pessoa não quer tomar
naquele momento, e que depois ninguém desfaz.

O pedido foi dar a "Minhas tarefas" o mesmo recurso de páginas dos projetos, com
abas no topo alternando entre Tarefas e Páginas, e mais duas capacidades que
projeto não tem: **compartilhar uma página com pessoas escolhidas** e uma aba
**"Compartilhado comigo"**.

## A decisão em uma frase

Uma página pessoal é uma `Page` do workspace **sem** vínculo em `ProjectPage`, e
o acesso a ela vem do dono e de compartilhamentos nominais — não de papel de
projeto nem de papel de workspace.

## Página sem projeto, e não wiki de workspace

O modelo já permitia: `Page.workspace` é FK direta e `Page.projects` é M2M
**através de** `ProjectPage`. Página sem linha em `ProjectPage` já era, do ponto
de vista do banco, uma página de workspace — só não havia rota que a criasse.
Nenhum campo novo, nenhuma migração de dados.

A alternativa era um wiki de workspace: página pública para todo mundo que
estivesse no workspace. Foi descartada porque **não é o que foi pedido e resolve
outro problema**. Wiki é publicação — serve para o que a organização precisa
saber. O que faltava aqui é caderno: serve para o que **eu** preciso lembrar. Os
dois podem coexistir um dia; misturá-los agora significaria decidir na tela, a
cada página, entre "quem entrar no workspace lê" e "só eu leio", que é
exatamente a decisão que a pessoa não quer tomar ao começar a escrever.

## Acesso por pessoa, e não público/privado

Página de projeto tira acesso da participação no projeto: `access=0` significa
"quem está no projeto lê". Sem projeto, "público" não tem contorno — o alcance
viraria o workspace inteiro, que é o wiki descartado acima.

Então o acesso a uma página pessoal tem duas fontes, e só duas:

1. **ser o dono**, e
2. **ter uma linha de compartilhamento** com papel `pode ler` ou `pode editar`.

Escolher o papel **por pessoa** é o modelo que Docs e Notion já ensinaram, e
custa pouco: um campo na linha de compartilhamento, e o editor já sabe ficar em
modo leitura porque é o que faz nas páginas travadas.

O campo `access` continua existindo no modelo e fica sem uso na página pessoal.
Preferimos deixá-lo inerte a reinterpretá-lo: dar um segundo significado ao mesmo
campo é o tipo de economia que se paga com um defeito de permissão depois.

## Negar com 404, nunca com 403

Quem não é dono nem tem compartilhamento recebe **404**. Um 403 responderia
"existe, mas não é sua" — e a existência de uma página pessoal de outra pessoa,
com o identificador dela na mão, já é informação que não deveria vazar.

## Compartilhar é privilégio do dono

Quem recebe `pode editar` escreve na página e não pode excluí-la, arquivá-la,
compartilhá-la com um terceiro nem movê-la. Sem isso, "compartilhei com uma
pessoa" viraria, na prática, "compartilhei com quem ela quiser", e o dono
perderia a conta de quem lê.

## Duas travas estruturais

1. **Só página sem projeto pode ser compartilhada.** Deixar página de projeto
   receber compartilhamento nominal criaria página com duas fontes de acesso
   concorrentes — a participação no projeto e a lista de convidados —, e a
   pergunta "quem pode ler isto?" passaria a ter duas respostas que podem
   divergir.
2. **Mover para um projeto apaga os compartilhamentos.** No projeto, quem manda
   é o projeto. Manter as duas fontes seria o mesmo problema pela porta dos
   fundos. A tela avisa antes de mover, dizendo quantas pessoas perdem acesso.

Ambas moram no servidor. Esconder o controle na tela não é regra.

## O que não precisou ser escrito

O editor, o versionamento, o bloqueio, o arquivamento e a edição colaborativa
foram **instanciados**, não reimplementados. O upstream tinha deixado as costuras
prontas sem usá-las: `projectId` já era opcional em todo o editor,
`EPageStoreType` já era um mapa de stores com um valor só, `BasePage` já recebia
os serviços por injeção, e `PageCoreService` do `live` já era abstrata com
`basePath` abstrato. A rota de anexo de workspace já aceitava `PAGE_DESCRIPTION`.

Isso mudou o tamanho do trabalho: o que sobrou foi a API pessoal, o
compartilhamento — que não existia em lugar nenhum do produto — e as abas.

## No `live`

Um tipo de documento novo, `personal_page`, e um serviço que só troca o caminho
base. A autorização **não** mudou de lugar: o `live` repassa o cookie e é a API
que decide. Quem não pode abrir a página toma 404 e o documento não abre.

## Consequências

- Página pessoal não aparece em busca de projeto, favoritos de projeto nem
  relatórios de projeto. É consequência de não ter projeto, e é o esperado.
- Excluir a conta de alguém leva as páginas pessoais junto (`owned_by` é
  `CASCADE`), inclusive as que essa pessoa compartilhou. Quem lia perde o acesso
  sem aviso — o mesmo que já acontece com qualquer conteúdo de quem sai.
- Um wiki de workspace continua possível depois, e não conflita: seria uma
  terceira fonte de acesso, sobre as mesmas `Page` sem projeto.
