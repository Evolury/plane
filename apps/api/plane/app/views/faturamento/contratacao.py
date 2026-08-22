# Copyright (c) 2026-present Evolury
# SPDX-License-Identifier: AGPL-3.0-only
# See the LICENSE file for details.

"""Contratar, trocar de plano e ver o que já foi cobrado — ver ADR 0021.

**Duas portas, porque o Asaas impõe duas.** Cartão vai pela página hospedada
deles — dado de cartão não passa por aqui, e é isso que mantém o PCI fora do
nosso escopo. PIX é assinatura criada por API, com o Asaas gerando a cobrança a
cada ciclo e avisando por e-mail, SMS e WhatsApp; não existe débito automático
até o Pix Automático entrar.

**O acesso é liberado pelo evento, não pelo retorno do navegador.** Quem volta
do checkout pode fechar a aba, perder a rede ou não voltar nunca. Só o webhook
prova pagamento — e é por isso que estas rotas terminam devolvendo um link, e
não um "pronto, liberado".

Tudo aqui vive sob `faturamento/`, o prefixo que o middleware deixa passar:
**pagar não pode depender de estar pago**.
"""

from datetime import date

from django.utils import timezone
from rest_framework import status
from rest_framework.response import Response

from plane.app.permissions import ROLE, allow_permission
from plane.app.views.base import BaseAPIView
from plane.db.models import Assinatura, Cobranca, Cupom, HistoricoDeAssinatura
from plane.utils import asaas, cupons, documentos, planos, proporcional, regua
from plane.utils.error_codes import ERROR_CODES

FORMA_PIX = "pix"
FORMA_CARTAO = "cartao"
FORMAS = (FORMA_PIX, FORMA_CARTAO)

FORMA_NO_ASAAS = {FORMA_PIX: "PIX", FORMA_CARTAO: "CREDIT_CARD"}


def _assinatura(slug):
    return Assinatura.objects.select_related("workspace").filter(workspace__slug=slug).first()


def _erro(codigo, **extras):
    return Response({"error_code": ERROR_CODES.get(codigo, 0), "error_message": codigo, **extras}, status=400)


class DadosDeCobrancaEndpoint(BaseAPIView):
    """Nome, documento, e-mail e telefone de quem paga."""

    @allow_permission(allowed_roles=[ROLE.ADMIN], level="WORKSPACE")
    def get(self, request, slug):
        assinatura = _assinatura(slug)
        if assinatura is None:
            return _erro("SEM_ASSINATURA")
        return Response(
            {
                "nome": assinatura.nome_de_cobranca,
                "cpf_cnpj": documentos.formatar(assinatura.cpf_cnpj),
                "email": assinatura.email_de_cobranca,
                "telefone": assinatura.telefone_de_cobranca,
                "completo": bool(assinatura.cpf_cnpj and assinatura.nome_de_cobranca),
            },
            status=status.HTTP_200_OK,
        )

    @allow_permission(allowed_roles=[ROLE.ADMIN], level="WORKSPACE")
    def post(self, request, slug):
        assinatura = _assinatura(slug)
        if assinatura is None:
            return _erro("SEM_ASSINATURA")

        documento = documentos.normalizar(request.data.get("cpf_cnpj", ""))
        if not documentos.valido(documento):
            # Dito aqui, na hora em que a pessoa digitou. O Asaas também
            # recusaria, mas três telas depois e com mensagem de gateway.
            return _erro("DOCUMENTO_INVALIDO")

        nome = (request.data.get("nome") or "").strip()
        email = (request.data.get("email") or "").strip()
        if not nome or not email:
            return _erro("DADOS_INCOMPLETOS")

        assinatura.cpf_cnpj = documento
        assinatura.nome_de_cobranca = nome
        assinatura.email_de_cobranca = email
        assinatura.telefone_de_cobranca = (request.data.get("telefone") or "").strip()
        # O cliente no Asaas guarda os mesmos dados; mudá-los aqui obriga a
        # recriá-lo lá na próxima contratação, e não a corrigir pela metade.
        assinatura.save()

        return Response({"completo": True}, status=status.HTTP_200_OK)


class ConferirCupomEndpoint(BaseAPIView):
    """Diz se o código vale **antes** de a pessoa escolher plano e pagar."""

    @allow_permission(allowed_roles=[ROLE.ADMIN], level="WORKSPACE")
    def post(self, request, slug):
        codigo = (request.data.get("codigo") or "").strip().upper()
        cupom = Cupom.objects.filter(codigo=codigo).first()

        try:
            cupons.conferir(cupom, timezone.now().date())
        except cupons.CupomRecusado as recusa:
            return _erro(recusa.motivo)

        return Response(
            {
                "codigo": cupom.codigo,
                "tipo": cupom.tipo,
                "valor": cupom.valor,
                "ciclos": cupom.ciclos,
                "descricao": cupom.descricao,
            },
            status=status.HTTP_200_OK,
        )


class ContratarEndpoint(BaseAPIView):
    @allow_permission(allowed_roles=[ROLE.ADMIN], level="WORKSPACE")
    def post(self, request, slug):
        assinatura = _assinatura(slug)
        if assinatura is None:
            return _erro("SEM_ASSINATURA")

        chave = request.data.get("plano")
        ciclo = request.data.get("ciclo")
        forma = request.data.get("forma")

        if not planos.existe(chave):
            return _erro("PLANO_INVALIDO", planos=list(planos.CHAVES))
        if ciclo not in planos.CICLOS:
            return _erro("CICLO_INVALIDO", ciclos=list(planos.CICLOS))
        if forma not in FORMAS:
            return _erro("FORMA_INVALIDA", formas=list(FORMAS))
        if not assinatura.cpf_cnpj or not assinatura.nome_de_cobranca:
            return _erro("DADOS_DE_COBRANCA_FALTANDO")

        hoje = timezone.now().date()
        cupom = None
        if request.data.get("cupom"):
            cupom = Cupom.objects.filter(codigo=str(request.data["cupom"]).strip().upper()).first()
            try:
                cupons.conferir(cupom, hoje)
            except cupons.CupomRecusado as recusa:
                return _erro(recusa.motivo)

        copia = planos.copia_para_contrato(chave, ciclo)
        valor_cheio = copia["valor_base"]
        valor_cobrado = cupons.valor_com_desconto(cupom, valor_cheio)
        primeiro_vencimento = cupons.primeira_cobranca(cupom, hoje)

        try:
            resultado = self._contratar_no_asaas(
                assinatura=assinatura,
                chave=chave,
                ciclo=ciclo,
                forma=forma,
                valor=valor_cobrado,
                vencimento=primeiro_vencimento,
            )
        except asaas.ErroDoAsaas as erro:
            # A recusa do Asaas volta inteira: "documento inválido" e "cartão
            # recusado" pedem ações diferentes de quem está na tela.
            return Response(
                {"error_message": "ASAAS_RECUSOU", "detalhe": erro.corpo or str(erro)},
                status=status.HTTP_502_BAD_GATEWAY,
            )

        anterior = assinatura.status
        for campo, valor in copia.items():
            setattr(assinatura, campo, valor)
        assinatura.cupom = cupom
        assinatura.promocao_termina_em = cupons.fim_da_promocao(cupom, hoje, planos.fim_do_ciclo, ciclo)
        assinatura.proxima_cobranca_em = primeiro_vencimento

        if cupom is not None and cupom.tipo == cupons.CORTESIA:
            # Cortesia libera na hora: não há pagamento a esperar. E tem fim
            # gravado, que é o que impede "grátis para sempre" em silêncio.
            assinatura.status = regua.EM_CORTESIA
            assinatura.pago_ate = primeiro_vencimento

        assinatura.save()

        if cupom is not None:
            Cupom.objects.filter(pk=cupom.pk).update(usos=cupom.usos + 1)

        HistoricoDeAssinatura.objects.create(
            assinatura=assinatura,
            evento="contratacao",
            de=anterior,
            para=assinatura.status,
            motivo=f"{chave}/{ciclo} por {forma}" + (f", cupom {cupom.codigo}" if cupom else ""),
        )

        return Response(resultado, status=status.HTTP_200_OK)

    def _contratar_no_asaas(self, *, assinatura, chave, ciclo, forma, valor, vencimento: date):
        descricao = f"QooWork {planos.plano(chave).nome} — {ciclo}"
        ciclo_asaas = planos.CICLOS_DO_ASAAS[ciclo]

        if forma == FORMA_CARTAO:
            # Cartão recorrente só existe pelo checkout: `chargeTypes:
            # RECURRENT` do Asaas não aceita PIX, e o cartão não pode passar
            # por nós.
            checkout = asaas.criar_checkout(
                valor_em_centavos=valor,
                descricao=descricao,
                ciclo_asaas=ciclo_asaas,
                primeiro_vencimento=vencimento.isoformat(),
                workspace_id=str(assinatura.workspace_id),
                retorno=self._retorno(assinatura.workspace.slug),
            )
            assinatura.asaas_checkout_id = checkout.get("id") or ""
            return {"forma": FORMA_CARTAO, "link": checkout.get("link"), "id": checkout.get("id")}

        cliente_id = assinatura.asaas_customer_id
        if not cliente_id:
            cliente = asaas.criar_cliente(
                nome=assinatura.nome_de_cobranca,
                cpf_cnpj=assinatura.cpf_cnpj,
                email=assinatura.email_de_cobranca,
                telefone=assinatura.telefone_de_cobranca,
                workspace_id=str(assinatura.workspace_id),
            )
            cliente_id = cliente.get("id")
            assinatura.asaas_customer_id = cliente_id or ""

        criada = asaas.criar_assinatura(
            cliente_id=cliente_id,
            valor_em_centavos=valor,
            ciclo_asaas=ciclo_asaas,
            primeiro_vencimento=vencimento.isoformat(),
            descricao=descricao,
            workspace_id=str(assinatura.workspace_id),
            forma="PIX",
        )
        assinatura.asaas_subscription_id = criada.get("id") or ""

        # O link da primeira cobrança é o que a tela mostra. Se ainda não
        # existir, não é erro: o Asaas manda por e-mail, SMS e WhatsApp, e o
        # webhook traz o link para o histórico assim que ela for criada.
        link = ""
        try:
            cobrancas = asaas.listar_cobrancas(assinatura_id=assinatura.asaas_subscription_id, limite=1)
            link = ((cobrancas.get("data") or [{}])[0]).get("invoiceUrl") or ""
        except asaas.ErroDoAsaas:
            link = ""

        return {"forma": FORMA_PIX, "link": link, "id": assinatura.asaas_subscription_id}

    def _retorno(self, slug):
        from plane.utils.host import base_host

        base = base_host(request=self.request, is_app=True)
        return {
            "sucesso": f"{base}/{slug}/settings/billing/?contratacao=sucesso",
            "cancelado": f"{base}/{slug}/settings/billing/?contratacao=cancelada",
            "expirado": f"{base}/{slug}/settings/billing/?contratacao=expirada",
        }


class TrocarPlanoEndpoint(BaseAPIView):
    @allow_permission(allowed_roles=[ROLE.ADMIN], level="WORKSPACE")
    def post(self, request, slug):
        assinatura = _assinatura(slug)
        if assinatura is None or not assinatura.plano:
            return _erro("SEM_ASSINATURA")

        chave = request.data.get("plano")
        if not planos.existe(chave):
            return _erro("PLANO_INVALIDO", planos=list(planos.CHAVES))
        if chave == assinatura.plano:
            return _erro("MESMO_PLANO")

        ciclo = request.data.get("ciclo") or assinatura.ciclo or planos.CICLO_MENSAL
        atual = planos.plano(assinatura.plano)
        novo = planos.plano(chave)
        subindo = planos.ORDEM.index(chave) > planos.ORDEM.index(assinatura.plano)

        if not subindo:
            excesso = self._excesso_no_plano_menor(assinatura, novo)
            if excesso:
                # Dizer **o que** precisa sair, e não "não é possível": o
                # cliente não tem como adivinhar qual limite ele estourou.
                return Response(
                    {"error_message": "ACIMA_DO_TETO", "precisa_sair": excesso},
                    status=status.HTTP_402_PAYMENT_REQUIRED,
                )

        copia = planos.copia_para_contrato(chave, ciclo)
        cobranca_extra = None

        if subindo and assinatura.pago_ate:
            # O ciclo corrente vai do vencimento anterior até `pago_ate`, que é
            # também o próximo vencimento. O que se cobra é a diferença sobre o
            # que ainda resta dele.
            diferenca = proporcional.diferenca_de_upgrade(
                valor_atual=atual.preco(ciclo),
                valor_novo=novo.preco(ciclo),
                hoje=timezone.now().date(),
                inicio=self._inicio_do_ciclo(assinatura, ciclo),
                fim=assinatura.pago_ate,
            )
            if diferenca > 0 and assinatura.asaas_customer_id:
                try:
                    cobranca_extra = asaas.criar_cobranca_avulsa(
                        cliente_id=assinatura.asaas_customer_id,
                        valor_em_centavos=diferenca,
                        vencimento=timezone.now().date().isoformat(),
                        descricao=f"QooWork — diferença proporcional para {novo.nome}",
                        workspace_id=str(assinatura.workspace_id),
                    )
                except asaas.ErroDoAsaas as erro:
                    return Response(
                        {"error_message": "ASAAS_RECUSOU", "detalhe": erro.corpo or str(erro)},
                        status=status.HTTP_502_BAD_GATEWAY,
                    )

        if assinatura.asaas_subscription_id:
            try:
                asaas.atualizar_assinatura(
                    assinatura.asaas_subscription_id,
                    value=asaas.reais(copia["valor_base"]),
                    cycle=planos.CICLOS_DO_ASAAS[ciclo],
                )
            except asaas.ErroDoAsaas as erro:
                return Response(
                    {"error_message": "ASAAS_RECUSOU", "detalhe": erro.corpo or str(erro)},
                    status=status.HTTP_502_BAD_GATEWAY,
                )

        de = assinatura.plano
        for campo, valor in copia.items():
            setattr(assinatura, campo, valor)
        assinatura.save()

        HistoricoDeAssinatura.objects.create(
            assinatura=assinatura,
            evento="troca_de_plano",
            de=de,
            para=chave,
            motivo="Upgrade imediato" if subindo else "Downgrade a partir do próximo ciclo",
        )

        return Response(
            {
                "plano": chave,
                "imediato": subindo,
                "diferenca": {
                    "link": cobranca_extra.get("invoiceUrl"),
                    "valor": cobranca_extra.get("value"),
                }
                if cobranca_extra
                else None,
            },
            status=status.HTTP_200_OK,
        )

    def _inicio_do_ciclo(self, assinatura, ciclo):
        """O ciclo corrente começou um ciclo antes de acabar."""
        if ciclo == planos.CICLO_ANUAL:
            return assinatura.pago_ate.replace(year=assinatura.pago_ate.year - 1)
        mes = assinatura.pago_ate.month - 1 or 12
        ano = assinatura.pago_ate.year - (1 if assinatura.pago_ate.month == 1 else 0)
        dia = min(assinatura.pago_ate.day, 28)
        return date(ano, mes, dia)

    def _excesso_no_plano_menor(self, assinatura, novo):
        from plane.utils import direitos

        excesso = {}
        workspace_id = assinatura.workspace_id

        assentos = direitos.uso_de_assentos(workspace_id)
        if assentos > novo.assentos:
            excesso["membros"] = assentos - novo.assentos

        convidados = direitos.uso_de_convidados(workspace_id)
        cota = novo.convidados_por_assento * novo.assentos
        if convidados > cota:
            excesso["convidados"] = convidados - cota

        teto_de_automacoes = novo.teto(planos.LIMITE_AUTOMACOES)
        if teto_de_automacoes is not None:
            ativas = direitos.uso_de_automacoes(workspace_id)
            if ativas > teto_de_automacoes:
                excesso["automacoes"] = ativas - teto_de_automacoes

        return excesso


class CobrancasEndpoint(BaseAPIView):
    """O histórico que a tela mostra — espelho local, sem falar com o Asaas."""

    @allow_permission(allowed_roles=[ROLE.ADMIN], level="WORKSPACE")
    def get(self, request, slug):
        cobrancas = Cobranca.objects.filter(assinatura__workspace__slug=slug).order_by("-vencimento")[:50]
        return Response(
            [
                {
                    "id": str(cobranca.id),
                    "status": cobranca.status,
                    "forma": cobranca.forma,
                    "valor": cobranca.valor,
                    "vencimento": cobranca.vencimento,
                    "pago_em": cobranca.pago_em,
                    "link": cobranca.link,
                }
                for cobranca in cobrancas
            ],
            status=status.HTTP_200_OK,
        )
