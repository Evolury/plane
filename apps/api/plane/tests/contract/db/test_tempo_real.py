# Copyright (c) 2026-present Evolury
# SPDX-License-Identifier: AGPL-3.0-only
# See the LICENSE file for details.

"""O aviso de que uma tarefa mudou (ADR 0013).

Quando uma automação atribuía um responsável, o cartão no quadro não mudava: o
responsável só aparecia recarregando a página. A causa não era a automação — é
que o produto não tinha como dizer ao cliente "mudou algo que não foi você".

O que estes testes trancam é o **contrato do aviso**, e em especial o que ele
NÃO carrega. O evento leva identificadores e nada mais. Mandar o dado da tarefa
obrigaria o servidor a decidir, por destinatário, quem pode ver cada campo — uma
segunda implementação das regras de permissão, paralela à da API, e toda
divergência entre as duas seria vazamento. Um teste que só conferisse "publicou"
deixaria essa porta aberta para a primeira pessoa que achasse prático mandar o
nome da tarefa junto.
"""

import json
from unittest.mock import patch

import pytest

from plane.db.models import Issue

from plane.utils import tempo_real
from plane.utils.tempo_real import CANAL, publicar_mudanca, publicar_notificacao, publicar_propriedade


@pytest.fixture
def redis_falso():
    """Troca a conexão por um espião e a devolve zerada depois.

    O `_cliente` é global por processo — sem restaurá-lo, um teste contaminaria
    o seguinte com o espião deste.
    """
    publicadas = []

    class Espiao:
        def publish(self, canal, mensagem):
            publicadas.append((canal, mensagem))

    anterior = tempo_real._cliente
    tempo_real._cliente = Espiao()
    try:
        yield publicadas
    finally:
        tempo_real._cliente = anterior


def carga(publicadas, indice=0):
    return json.loads(publicadas[indice][1])


@pytest.mark.contract
class TestOQueOAvisoCarrega:
    def test_publica_no_canal_combinado(self, redis_falso):
        """O nome do canal é contrato com o `live`; mudar de um lado só o desliga."""
        publicar_mudanca("issue.activity.updated", "tarefa-1", "projeto-1", "pessoa-1")

        assert len(redis_falso) == 1
        assert redis_falso[0][0] == CANAL

    def test_leva_identificadores_e_o_tipo(self, redis_falso):
        publicar_mudanca("issue.activity.updated", "tarefa-1", "projeto-1", "pessoa-1")

        assert carga(redis_falso) == {
            "tipo": "alterada",
            "projeto": "projeto-1",
            "tarefa": "tarefa-1",
            "ator": "pessoa-1",
        }

    def test_nao_leva_conteudo_nenhum(self, redis_falso):
        """A afirmação que sustenta o desenho inteiro — ver o cabeçalho.

        Escrito como lista fechada de chaves, e não como "não contém `name`":
        assim, quem acrescentar um campo novo ao aviso tem de passar por aqui e
        decidir de propósito, em vez de descobrir depois que vazou.
        """
        publicar_mudanca("issue.activity.updated", "tarefa-1", "projeto-1", "pessoa-1")

        assert set(carga(redis_falso)) == {"tipo", "projeto", "tarefa", "ator"}

    def test_ator_ausente_vira_nulo(self, redis_falso):
        """Sem ator, o cliente não tem como reconhecer o próprio eco — e tudo bem.

        O que não pode é a chave sumir: o cliente lê `dados.ator` sem guarda.
        """
        publicar_mudanca("issue.activity.updated", "tarefa-1", "projeto-1", None)

        assert carga(redis_falso)["ator"] is None


class Linha:
    """O mínimo de uma linha de histórico que o publicador lê."""

    def __init__(self, field, new_value=None):
        self.field = field
        self.new_value = new_value


@pytest.mark.contract
class TestEntrarESairDoQuadro:
    """Fase 2: o tipo sozinho não distingue arquivar de editar.

    As duas chegam como `issue.activity.updated` — só o campo denuncia. Sem
    olhar as linhas, arquivar por automação viraria "alterada", o cliente
    rebuscaria a tarefa e a manteria na tela, arquivada.
    """

    def test_criar_pede_a_lista(self, redis_falso):
        publicar_mudanca("issue.activity.created", "tarefa-1", "projeto-1", "pessoa-1")
        assert carga(redis_falso)["tipo"] == "criada"

    def test_excluir_tira_do_quadro(self, redis_falso):
        publicar_mudanca("issue.activity.deleted", "tarefa-1", "projeto-1", "pessoa-1")
        assert carga(redis_falso)["tipo"] == "removida"

    def test_arquivar_tira_do_quadro(self, redis_falso):
        publicar_mudanca(
            "issue.activity.updated", "tarefa-1", "projeto-1", "pessoa-1", linhas=[Linha("archived_at", "2026-08-17")]
        )
        assert carga(redis_falso)["tipo"] == "removida"

    def test_desarquivar_traz_de_volta(self, redis_falso):
        """Voltar ao quadro é entrar, e entrar depende do filtro: mesma resposta que criar."""
        publicar_mudanca(
            "issue.activity.updated", "tarefa-1", "projeto-1", "pessoa-1", linhas=[Linha("archived_at", "restore")]
        )
        assert carga(redis_falso)["tipo"] == "criada"

    def test_edicao_comum_continua_sendo_alteracao(self, redis_falso):
        """Sem isto, tratar toda atualização como saída passaria nos testes acima."""
        publicar_mudanca(
            "issue.activity.updated", "tarefa-1", "projeto-1", "pessoa-1", linhas=[Linha("priority", "urgent")]
        )
        assert carga(redis_falso)["tipo"] == "alterada"

    def test_arquivamento_no_meio_de_outras_mudancas_ainda_e_saida(self, redis_falso):
        """Uma edição pode gravar várias linhas; basta uma ser o arquivamento."""
        publicar_mudanca(
            "issue.activity.updated",
            "tarefa-1",
            "projeto-1",
            "pessoa-1",
            linhas=[Linha("priority", "urgent"), Linha("archived_at", "2026-08-17")],
        )
        assert carga(redis_falso)["tipo"] == "removida"


@pytest.mark.contract
class TestOQueNaoViraAviso:
    """Publicar o que ninguém consome é ruído que parece funcionalidade."""

    @pytest.mark.parametrize(
        "tipo",
        [
            "issue_draft.activity.updated",  # rascunho não é cartão de ninguém
            "issue_reaction.activity.created",  # não aparece no cartão
            "attachment.activity.created",
        ],
    )
    def test_tipo_que_nao_muda_o_cartao_nao_publica(self, redis_falso, tipo):
        publicar_mudanca(tipo, "tarefa-1", "projeto-1", "pessoa-1")

        assert redis_falso == []

    @pytest.mark.parametrize(
        "issue_id,project_id",
        [(None, "projeto-1"), ("tarefa-1", None), (None, None)],
    )
    def test_sem_identificador_nao_publica(self, redis_falso, issue_id, project_id):
        """Aviso sem alvo não teria como ser entregue, e o `live` o descartaria."""
        publicar_mudanca("issue.activity.updated", issue_id, project_id, "pessoa-1")

        assert redis_falso == []


@pytest.mark.contract
class TestCicloEModuloContamComoAlteracao:
    """No quadro do projeto, ciclo e módulo são campos do cartão como outro qualquer."""

    @pytest.mark.parametrize(
        "tipo",
        [
            "cycle.activity.created",
            "cycle.activity.deleted",
            "module.activity.created",
            "module.activity.deleted",
        ],
    )
    def test_publica_como_alterada(self, redis_falso, tipo):
        publicar_mudanca(tipo, "tarefa-1", "projeto-1", "pessoa-1")

        assert len(redis_falso) == 1
        assert carga(redis_falso)["tipo"] == "alterada"


@pytest.mark.contract
class TestValorDePropriedadePersonalizada:
    """Fase 3: a gravação de valor não passa pelo funil de `issue_activity`.

    Ela escreve `IssueActivity` direto, e era por isso que propriedade marcada
    para o cartão continuava exigindo recarga: nenhum aviso saía dali.

    O aviso é de tipo próprio porque a resposta do cliente também é — o valor
    não vive no store de tarefas, e sim numa chave do PROJETO inteiro. Rebuscar
    a tarefa não o traria.
    """

    def test_publica_com_tipo_proprio(self, redis_falso):
        publicar_propriedade("tarefa-1", "projeto-1", "pessoa-1")

        assert len(redis_falso) == 1
        assert carga(redis_falso)["tipo"] == "propriedade"

    def test_leva_identificadores_e_nada_mais(self, redis_falso):
        """Nem o id da propriedade, nem o valor: o cliente rebusca a chave inteira."""
        publicar_propriedade("tarefa-1", "projeto-1", "pessoa-1")

        assert carga(redis_falso) == {
            "tipo": "propriedade",
            "projeto": "projeto-1",
            "tarefa": "tarefa-1",
            "ator": "pessoa-1",
        }

    @pytest.mark.parametrize("issue_id,project_id", [(None, "projeto-1"), ("tarefa-1", None)])
    def test_sem_identificador_nao_publica(self, redis_falso, issue_id, project_id):
        publicar_propriedade(issue_id, project_id, "pessoa-1")

        assert redis_falso == []

    def test_redis_quebrado_nao_derruba_a_gravacao(self):
        """Mesma política do outro publicador: aviso é conforto de tela."""

        class Quebrado:
            def publish(self, canal, mensagem):
                raise ConnectionError("redis fora do ar")

        anterior = tempo_real._cliente
        tempo_real._cliente = Quebrado()
        try:
            with patch("plane.utils.tempo_real.log_exception") as registrou:
                publicar_propriedade("tarefa-1", "projeto-1", "pessoa-1")
            assert registrou.called
        finally:
            tempo_real._cliente = anterior


@pytest.mark.contract
class TestAFiacaoDaPropriedade:
    """A regressão que os testes acima NÃO pegam: alguém remover a chamada.

    Testar `publicar_propriedade` sozinha prova que a função sabe publicar, e
    não que ela é chamada de onde precisa. A lacuna apareceu numa injeção de
    defeito: apagar a chamada em `registrar_atividade_de_propriedade` deixou a
    suíte inteira verde — exatamente o defeito que a fase 3 corrige, de volta e
    em silêncio.
    """

    @pytest.mark.django_db
    def test_gravar_valor_avisa_a_tela(self, db, workspace, create_user):
        from plane.db.models import IssueProperty, Project, State
        from plane.utils.automacoes.despacho import registrar_atividade_de_propriedade

        projeto = Project.objects.create(name="Fiação", identifier="FIA", workspace=workspace)
        estado = State.objects.create(name="A fazer", project=projeto, workspace=workspace, group="unstarted")
        tarefa = Issue.objects.create(name="t", project=projeto, workspace=workspace, state=estado, sequence_id=1)
        propriedade = IssueProperty.objects.create(
            name="Local", project=projeto, workspace=workspace, property_type="TEXT"
        )

        with patch("plane.utils.automacoes.despacho.publicar_propriedade") as avisou:
            registrar_atividade_de_propriedade(
                tarefa=tarefa, propriedade=propriedade, de="", para="Galpão", actor_id=create_user.id
            )

        assert avisou.called, "gravar valor de propriedade tem de avisar a tela"
        assert avisou.call_args.kwargs["issue_id"] == tarefa.id
        assert avisou.call_args.kwargs["project_id"] == projeto.id

    @pytest.mark.django_db
    def test_valor_que_nao_mudou_nao_avisa(self, db, workspace, create_user):
        """Sem isto, avisar sempre passaria no teste acima."""
        from plane.db.models import IssueProperty, Project, State
        from plane.utils.automacoes.despacho import registrar_atividade_de_propriedade

        projeto = Project.objects.create(name="Fiação 2", identifier="FI2", workspace=workspace)
        estado = State.objects.create(name="A fazer", project=projeto, workspace=workspace, group="unstarted")
        tarefa = Issue.objects.create(name="t", project=projeto, workspace=workspace, state=estado, sequence_id=1)
        propriedade = IssueProperty.objects.create(
            name="Local", project=projeto, workspace=workspace, property_type="TEXT"
        )

        with patch("plane.utils.automacoes.despacho.publicar_propriedade") as avisou:
            registrar_atividade_de_propriedade(
                tarefa=tarefa, propriedade=propriedade, de="Galpão", para="Galpão", actor_id=create_user.id
            )

        assert not avisou.called


@pytest.mark.contract
class TestFalhaNaoDerrubaOHistorico:
    """A razão de o aviso ser silencioso.

    Ele roda no funil de `issue_activity`, logo depois de o histórico ser
    gravado. Redis fora do ar não pode transformar "arrastei um cartão" em erro:
    sem aviso, a tela volta a se comportar como antes — desatualizada, e não
    quebrada.
    """

    def test_redis_quebrado_nao_levanta(self):
        class Quebrado:
            def publish(self, canal, mensagem):
                raise ConnectionError("redis fora do ar")

        anterior = tempo_real._cliente
        tempo_real._cliente = Quebrado()
        try:
            with patch("plane.utils.tempo_real.log_exception") as registrou:
                publicar_mudanca("issue.activity.updated", "tarefa-1", "projeto-1", "pessoa-1")
            assert registrou.called, "engolir o erro sem registrar esconderia a falha"
        finally:
            tempo_real._cliente = anterior

    def test_conexao_quebrada_e_solta_para_a_proxima_tentar_de_novo(self):
        """Sem soltar, um cliente inutilizável repetiria o erro para sempre."""

        class Quebrado:
            def publish(self, canal, mensagem):
                raise ConnectionError("redis fora do ar")

        anterior = tempo_real._cliente
        tempo_real._cliente = Quebrado()
        try:
            with patch("plane.utils.tempo_real.log_exception"):
                publicar_mudanca("issue.activity.updated", "tarefa-1", "projeto-1", "pessoa-1")
            assert tempo_real._cliente is None
        finally:
            tempo_real._cliente = anterior


@pytest.mark.contract
class TestAvisoDeNotificacao:
    """A caixa de entrada (ADR 0013).

    O sino só buscava ao abrir a tela: uma notificação que chegasse com o
    produto aberto ficava invisível até recarregar. É o mesmo defeito do cartão,
    num lugar em que dói mais — notificação é justamente o que existe para
    avisar.

    Este aviso é o único sem projeto: notificação é de uma PESSOA, e o sino vive
    fora de qualquer quadro. Quem separa por destinatário é o `live`.
    """

    def test_publica_a_lista_de_destinatarios(self, redis_falso):
        publicar_notificacao(["pessoa-1", "pessoa-2"])

        assert len(redis_falso) == 1
        assert carga(redis_falso) == {"tipo": "notificacao", "usuarios": ["pessoa-1", "pessoa-2"]}

    def test_vai_uma_mensagem_so(self, redis_falso):
        """Uma tarefa com muitos inscritos não pode virar dezenas de publicações."""
        publicar_notificacao([f"pessoa-{i}" for i in range(50)])

        assert len(redis_falso) == 1

    def test_nao_leva_projeto_nem_tarefa(self, redis_falso):
        """A ausência é o desenho, não esquecimento: o roteamento é por pessoa."""
        publicar_notificacao(["pessoa-1"])

        assert set(carga(redis_falso)) == {"tipo", "usuarios"}

    @pytest.mark.parametrize("entrada", [[], None, [None, ""]])
    def test_sem_destinatario_nao_publica(self, redis_falso, entrada):
        publicar_notificacao(entrada)

        assert redis_falso == []

    def test_descarta_vazios_no_meio(self, redis_falso):
        """Sem isto, um `None` na lista viraria a string "None" como destinatário."""
        publicar_notificacao(["pessoa-1", None, "", "pessoa-2"])

        assert carga(redis_falso)["usuarios"] == ["pessoa-1", "pessoa-2"]
