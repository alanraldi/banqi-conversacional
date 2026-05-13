"""Processadores para cada tipo de evento webhook recebido do backend banQi."""

from __future__ import annotations

import logging
from typing import Any

logger = logging.getLogger(__name__)


def handle_consent_term_file_ready(data: dict[str, Any]) -> str | None:
    """Evento: PDF do termo de consentimento gerado."""
    pdf_url = data.get("pdfUrl") or data.get("pdf_url") or data.get("data", {}).get("pdfUrl", "")
    if pdf_url:
        return (
            f"Seu Termo de Consentimento está pronto! 📄\n"
            f"Acesse aqui: {pdf_url}\n\n"
            "Leia com atenção e me diga: você aceita os termos? (responda *SIM* ou *NÃO*)"
        )
    return (
        "Seu Termo de Consentimento foi gerado! 📄\n"
        "Leia com atenção e me diga: você aceita os termos? (responda *SIM* ou *NÃO*)"
    )


def handle_no_offer_available(data: dict[str, Any]) -> str | None:
    """Evento: cliente sem oferta disponível ou erro no processo."""
    error_code = data.get("errorCode") or data.get("error_code", "")
    messages = {
        "PDF_GENERATION_ERROR": "Tivemos um problema técnico ao gerar seu documento. Tente novamente em alguns instantes.",
        "TOKEN_GENERATION_ERROR": "Não conseguimos verificar seus dados no momento. Tente novamente mais tarde.",
        "ELIGIBILITY_REJECTED": "Infelizmente não encontramos uma oferta de empréstimo consignado disponível para você agora.",
        "SIMULATION_ERROR": "Tivemos um problema ao simular o empréstimo. Tente novamente em alguns instantes.",
    }
    return messages.get(error_code, "Não foi possível processar sua solicitação no momento. Tente novamente mais tarde.")


def handle_simulation_ready(data: dict[str, Any]) -> str | None:
    """Evento: simulação automática disponível após aceite do termo."""
    sim_data = data.get("data", data)
    simulations = sim_data.get("simulations", [])
    if not simulations:
        return "Sua simulação está pronta! 🎉\nDeseja prosseguir com a oferta disponível ou prefere simular com outros valores?"

    sim = simulations[0] if isinstance(simulations, list) else simulations
    valor = sim.get("amount") or sim.get("valor", "")
    parcelas = sim.get("numInstallments") or sim.get("parcelas", "")
    parcela_valor = sim.get("installmentAmount") or sim.get("valorParcela", "")
    taxa = sim.get("monthlyRate") or sim.get("taxaMensal", "")
    data_dep = sim.get("disbursementDate") or sim.get("dataDeposito", "")

    linhas = ["✅ *Proposta disponível para você:*\n"]
    if valor:
        linhas.append(f"💰 Valor a receber: R$ {valor}")
    if parcelas:
        linhas.append(f"📅 Parcelas: {parcelas}x")
    if parcela_valor:
        linhas.append(f"💳 Valor de cada parcela: R$ {parcela_valor}")
    if taxa:
        linhas.append(f"📊 Taxa mensal (CET): {taxa}%")
    if data_dep:
        linhas.append(f"🗓 Previsão de depósito: {data_dep}")
    linhas.append("\nDeseja prosseguir com esses valores ou prefere simular com outros valores?")
    return "\n".join(linhas)


def handle_simulation_completed(data: dict[str, Any]) -> str | None:
    """Evento: simulação personalizada concluída."""
    return handle_simulation_ready(data)


def handle_proposal_created(data: dict[str, Any]) -> str | None:
    """Evento: proposta criada com sucesso. Não envia mensagem — o agente prossegue internamente."""
    id_proposal = data.get("idProposal") or data.get("id_proposal", "")
    logger.info("handle_proposal_created: id_proposal=%s", id_proposal)
    return None


def handle_proposal_status_update(data: dict[str, Any]) -> str | None:
    """Evento: atualização de status da proposta durante etapa 7."""
    new_status = data.get("newStatus") or data.get("new_status", "")
    disbursement_date = data.get("disbursementDate") or data.get("data", {}).get("disbursementDate", "")
    amount = data.get("amount") or data.get("data", {}).get("amount", "")

    messages = {
        "ACCEPTED": "Proposta recebida! Estamos processando seu contrato. ⏳",
        "SIGNED": "Ótima notícia! Seu contrato foi assinado digitalmente. ✍️",
        "CCB_GENERATED": "Cédula de Crédito Bancária registrada com sucesso. 📋",
        "FORMALIZED": "Averbação aprovada! Aguardando o desembolso. 🔄",
        "PENDING_DISBURSEMENT": f"Desembolso agendado para {disbursement_date}. 📅" if disbursement_date else "Desembolso agendado. Em breve o valor estará na sua conta. 📅",
        "DISBURSED": f"R$ {amount} creditado na sua conta banQi! Bom proveito! 🎉" if amount else "Valor creditado na sua conta banQi! Bom proveito! 🎉",
        "CANCELED": "Sua proposta foi cancelada. Precisa de ajuda? Estou aqui!",
        "ERROR": "Ocorreu um erro no processamento da sua proposta. Entre em contato com o suporte banQi.",
    }

    msg = messages.get(new_status)
    if not msg:
        logger.warning("handle_proposal_status_update: newStatus desconhecido '%s'", new_status)
    return msg
