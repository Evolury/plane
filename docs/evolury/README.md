# Documentação Evolury

Esta árvore documenta o que a Evolury constrói por cima da base herdada do
Plane CE — o complemento em prosa do comentário `Evolury:` no código. O que é
herdado se explica pelo próprio upstream; o que é nosso se explica aqui.

## Estrutura

```
evolury/
├── decisoes/            # ADRs — decisões de arquitetura numeradas
│   └── NNNN-titulo.md
├── processos/           # como o time trabalha, quando o "como" precisa sobreviver
│   └── <nome>.md
└── funcionalidades/     # uma pasta por funcionalidade própria
    └── <nome>/
        ├── especificacao.md    # comportamento, UX, regras de negócio
        ├── arquitetura.md      # modelo de dados, API, stores, componentes
        ├── compatibilidade.md  # matriz de interação com recursos existentes
        ├── manual.md           # comportamento observável, fonte do manual do usuário
        └── backlog.md          # fases, itens e critérios de aceite
```

## Convenções

**ADRs (`decisoes/`).** Um arquivo por decisão, numerado em sequência
(`0001-...`, `0002-...`). Um ADR aceito não é editado: se a decisão mudar, um
ADR novo a substitui e o antigo ganha a nota "Substituído por NNNN". Cada ADR
registra contexto, decisão, alternativas consideradas e consequências — o
objetivo é que, anos depois, alguém entenda _por que_ o código é assim sem
arqueologia de git.

**Funcionalidades (`funcionalidades/`).** O ciclo é documentação primeiro:

1. `especificacao.md` aprovada antes de qualquer código;
2. `arquitetura.md` fecha o desenho técnico (decisões estruturais viram ADR);
3. `backlog.md` quebra em fases com critérios de aceite — os PRs de
   implementação referenciam os itens;
4. `compatibilidade.md` é executada como checklist antes de considerar a
   funcionalidade entregue;
5. o status no índice [docs/README.md](../README.md) acompanha o progresso
   (Planejada → Em desenvolvimento → Entregue).

**Processos (`processos/`).** Rotina que se repete e cuja execução precisa ser
igual entre uma vez e outra — hoje, a
[revisão do upstream](processos/revisao-do-upstream.md), que anda
junto do seu [histórico](processos/historico-de-revisoes.md). Processo com log
é processo que se pode auditar: cada execução diz de onde partiu, o que achou e
o que decidiu, e a execução seguinte começa lendo a anterior.

**Manual (`manual.md`).** Opcional, e vale a pena quando a funcionalidade chega
ao usuário final: descreve **o que acontece**, em linguagem de quem usa,
organizado por situação em vez de por fase de implementação. É a fonte para o
material de treinamento — sem raciocínio de projeto, que mora no ADR, e sem
detalhe de implementação, que mora na arquitetura. Escrito depois da entrega,
quando o comportamento já é fato.

**Relação com o código.** Arquivo herdado do upstream que for alterado por uma
funcionalidade recebe o comentário `Evolury:` apontando o porquê — e a
`arquitetura.md` da funcionalidade lista todos os pontos de integração. Isso
mantém o delta do fork auditável nos dois sentidos: do código para a doc e da
doc para o código.
