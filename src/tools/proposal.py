"""Tool de criação de proposta de empréstimo consignado — etapa 4 do fluxo.

create_proposal: submete a proposta com dados pessoais, endereço e conta bancária.
O processamento é assíncrono — aguarda webhook PROPOSAL_CREATED com o idProposal.
"""

from __future__ import annotations

import logging
import os
from typing import Any

import httpx
from strands import tool

logger = logging.getLogger(__name__)

_BASE_URL_ENV = "BANQI_API_BASE_URL"
_TIMEOUT = 30


def _make_headers(phone: str, cpf: str) -> dict[str, str]:
    return {
        "x-whatsapp-phone": phone,
        "x-document": cpf,
        "x-partner": "banqi-wpp",
        "Content-Type": "application/json",
    }


def _base_url() -> str:
    url = os.environ.get(_BASE_URL_ENV, "")
    if not url:
        raise RuntimeError(f"Variável de ambiente não configurada: {_BASE_URL_ENV}")
    return url.rstrip("/")


@tool
def create_proposal(
    phone: str,
    cpf: str,
    id_simulation: str,
    email: str,
    address: dict[str, str],
    bank_account: dict[str, str],
) -> dict[str, Any]:
    """Cria uma proposta de empréstimo consignado com base em uma simulação aprovada.

    O processamento é assíncrono: a resposta 202 indica que a proposta foi submetida
    e será confirmada via webhook PROPOSAL_CREATED contendo o idProposal.

    Campos obrigatórios do address:
        zipCode, street, number, complement, neighborhood, city, state

    Campos obrigatórios do bank_account:
        bankCode, agency, accountNumber, accountDigit,
        accountType (CHECKING | SAVINGS | PAYMENT | SALARY)

    Args:
        phone: Telefone do cliente em formato E.164.
        cpf: CPF do cliente com 11 dígitos, sem formatação.
        id_simulation: UUID da simulação escolhida pelo cliente (obtido do webhook ou get_simulations).
        email: E-mail do cliente para envio da documentação.
        address: Dicionário com os dados de endereço do cliente.
        bank_account: Dicionário com os dados bancários para crédito do empréstimo.

    Returns:
        dict com campos:
        - status: "PENDING" | "INVALID_SIMULATION" | "VALIDATION_ERROR" | "ERROR"
        - message: Descrição legível do resultado.
        - http_status: Código HTTP retornado pela API.
        - detail: Detalhes do erro quando aplicável.
    """
    headers = _make_headers(phone, cpf)

    payload: dict[str, Any] = {
        "idSimulation": id_simulation,
        "email": email,
        "address": {
            "zipCode": address.get("zipCode", ""),
            "street": address.get("street", ""),
            "number": address.get("number", ""),
            "complement": address.get("complement", ""),
            "neighborhood": address.get("neighborhood", ""),
            "city": address.get("city", ""),
            "state": address.get("state", ""),
        },
        "bankAccount": {
            "bankCode": bank_account.get("bankCode", ""),
            "agency": bank_account.get("agency", ""),
            "accountNumber": bank_account.get("accountNumber", ""),
            "accountDigit": bank_account.get("accountDigit", ""),
            "accountType": bank_account.get("accountType", ""),
        },
    }

    try:
        with httpx.Client(timeout=_TIMEOUT) as client:
            resp = client.post(
                f"{_base_url()}/v1/whatsapp/proposals",
                headers=headers,
                json=payload,
            )

        logger.info(
            "create_proposal: http_status=%s phone=%s id_simulation=%s",
            resp.status_code,
            phone[:6] + "****",
            id_simulation,
        )

        if resp.status_code == 202:
            try:
                body = resp.json()
            except Exception:
                body = {}
            return {
                "status": "PENDING",
                "message": (
                    "Proposta submetida com sucesso. "
                    "Aguardando webhook PROPOSAL_CREATED para confirmar o idProposal."
                ),
                "http_status": 202,
                "id_correlation": body.get("idCorrelation"),
            }

        if resp.status_code == 412:
            try:
                body = resp.json()
            except Exception:
                body = resp.text
            logger.warning(
                "create_proposal: simulação inválida id_simulation=%s body=%s",
                id_simulation,
                body,
            )
            return {
                "status": "INVALID_SIMULATION",
                "message": (
                    f"A simulação '{id_simulation}' é inválida ou expirou. "
                    "O cliente precisa criar uma nova simulação antes de submeter a proposta."
                ),
                "http_status": 412,
                "detail": body,
            }

        if resp.status_code == 422:
            try:
                body = resp.json()
            except Exception:
                body = resp.text
            logger.warning("create_proposal: erro de validação body=%s", body)
            return {
                "status": "VALIDATION_ERROR",
                "message": "Dados inválidos na proposta. Verifique e corrija os campos antes de tentar novamente.",
                "http_status": 422,
                "detail": body,
            }

        try:
            body = resp.json()
        except Exception:
            body = resp.text

        logger.error("create_proposal: resposta inesperada %s body=%s", resp.status_code, body)
        return {
            "status": "ERROR",
            "message": f"Erro inesperado ao criar proposta (HTTP {resp.status_code}).",
            "http_status": resp.status_code,
            "detail": body,
        }

    except RuntimeError as exc:
        logger.error("create_proposal: configuração inválida — %s", exc)
        return {"status": "ERROR", "message": str(exc), "http_status": None}
    except httpx.TimeoutException:
        logger.error("create_proposal: timeout ao chamar API banQi")
        return {
            "status": "ERROR",
            "message": "Timeout ao conectar com a API banQi. Tente novamente.",
            "http_status": None,
        }
    except httpx.RequestError as exc:
        logger.error("create_proposal: erro de rede — %s", exc)
        return {
            "status": "ERROR",
            "message": f"Erro de conexão com a API banQi: {exc}",
            "http_status": None,
        }
