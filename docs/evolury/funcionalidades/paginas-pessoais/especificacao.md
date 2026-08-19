# Páginas pessoais — especificação

Páginas em "Minhas tarefas": criadas fora de qualquer projeto, com abas no topo
alternando entre **Tarefas** e **Páginas**, compartilháveis com pessoas
escolhidas e uma aba **Compartilhado comigo**.

Decisões de arquitetura em [ADR 0015](../../decisoes/0015-paginas-pessoais.md).

## O que é uma página pessoal

Uma `Page` do workspace **sem** vínculo em `ProjectPage`. Não existe campo que a
marque como pessoal: a ausência do vínculo é a definição.

Ela tem tudo o que uma página de projeto tem — editor colaborativo, versões,
bloqueio, arquivamento, duplicação, anexos, ícone e capa. O que muda é de quem
ela é e quem a enxerga.

## Abas

Uma barra secundária, no mesmo desenho das abas de páginas de projeto —
sublinhado na ativa:

| Aba                      | O que mostra                                                                  |
| ------------------------ | ----------------------------------------------------------------------------- |
| **Tarefas**              | o que já existia: etapas, filtros, layouts                                    |
| **Páginas**              | as suas páginas pessoais; à direita, "Arquivadas", busca, ordenação e filtros |
| **Compartilhado comigo** | páginas pessoais **de outras pessoas** compartilhadas com você                |

O cabeçalho principal mantém a migalha "Minhas tarefas" e troca a ação da
direita conforme a aba: gestão de etapas e filtros na de Tarefas, **Nova página**
na de Páginas.

O editor de uma página fica **fora** desse layout — cabeçalho próprio, com
migalha `Minhas tarefas › Páginas › <título>`, sem abas e sem controles de
tarefa.

## Acesso

Duas fontes, e só duas:

| Quem                         | Pode                                          |
| ---------------------------- | --------------------------------------------- |
| dono                         | tudo                                          |
| compartilhado, `pode editar` | ler e escrever no conteúdo e nas propriedades |
| compartilhado, `pode ler`    | só ler                                        |
| resto                        | **404** — nem a existência da página vaza     |

Excluir, arquivar, compartilhar e mover são **sempre** do dono, mesmo para quem
pode editar.

Página pessoal não tem público/privado. O campo `access` do modelo continua lá e
fica sem uso — ver o ADR.

## Compartilhamento

O dono abre o menu de ações da página e escolhe pessoas do workspace, com papel
**Pode ler** ou **Pode editar** por pessoa. A lista de quem já tem acesso fica no
mesmo lugar, com remoção.

Duas regras que moram no servidor, não na tela:

1. **Só página sem projeto pode ser compartilhada.**
2. **Mover para um projeto apaga os compartilhamentos** — a tela avisa antes,
   dizendo quantas pessoas perdem acesso.

## Mover entre pessoal e projeto

Nos dois sentidos: rascunhar no pessoal e publicar no projeto, ou recolher do
projeto para o pessoal. Mover é criar ou apagar a linha em `ProjectPage`.

Só o dono move. Da pessoal para o projeto, é preciso poder criar página naquele
projeto.

## Arquivadas

A única divisão dentro da aba Páginas é ativa x arquivada, e ela é um link à
direita da barra, não uma segunda linha de abas. Excluir exige arquivar antes,
como nas páginas de projeto.
