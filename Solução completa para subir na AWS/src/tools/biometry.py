"""Tools de biometria facial — etapa 5 do fluxo de empréstimo consignado.

start_biometry: inicia o processo de liveness + face match (Único), retorna BioLink.
continue_biometry: consulta resultado da biometria e avança o fluxo.
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
def start_biometry(phone: str, cpf: str, id_proposal: str) -> dict[str, Any]:
    """Inicia o processo de biometria facial para o cliente.

    Retorna o BioLink que deve ser enviado ao cliente via WhatsApp para ele fazer
    o liveness + face match em seu próprio dispositivo.

    Args:
        phone: Telefone do cliente em formato E.164.
        cpf: CPF do cliente com 11 dígitos, sem formatação.
        id_proposal: UUID da proposta criada na etapa 4.

    Returns:
        dict com status: "STARTED" | "ERROR"
        bio_link: URL para o cliente fazer a biometria.
        id_anti_fraud: ID do processo antifraude.
    """
    headers = _make_headers(phone, cpf)

    try:
        with httpx.Client(timeout=_TIMEOUT) as client:
            resp = client.post(f"{_base_url()}/v1/whatsapp/proposals/{id_proposal}/biometry", headers=headers)

        if resp.status_code in (200, 201):
            body = resp.json() if resp.content else {}
            return {
                "status": "STARTED",
                "message": "Biometria iniciada. Enviar o BioLink ao cliente.",
                "http_status": resp.status_code,
                "bio_link": body.get("bioLink", ""),
                "id_anti_fraud": body.get("idAntiFraud", ""),
            }

        return {"status": "ERROR", "message": f"Erro ao iniciar biometria (HTTP {resp.status_code}).", "http_status": resp.status_code}

    except RuntimeError as exc:
        return {"status": "ERROR", "message": str(exc), "http_status": None}
    except httpx.TimeoutException:
        return {"status": "ERROR", "message": "Timeout ao iniciar biometria.", "http_status": None}
    except httpx.RequestError as exc:
        return {"status": "ERROR", "message": f"Erro de conexão: {exc}", "http_status": None}


@tool
def continue_biometry(
    phone: str,
    cpf: str,
    id_proposal: str,
    id_anti_fraud: str,
    id_biometric: str,
    provider: str,
) -> dict[str, Any]:
    """Consulta o resultado da biometria e avança o fluxo.

    Args:
        phone: Telefone do cliente em formato E.164.
        cpf: CPF do cliente com 11 dígitos, sem formatação.
        id_proposal: UUID da proposta.
        id_anti_fraud: ID antifraude retornado em start_biometry.
        id_biometric: ID da biometria fornecido pelo SDK Único.
        provider: Provedor da biometria (ex: "UNICO").

    Returns:
        dict com status: "APPROVED" | "PENDING" | "DENIED" | "ERROR"
    """
    headers = _make_headers(phone, cpf)
    payload = {"idAntiFraud": id_anti_fraud, "idBiometric": id_biometric, "provider": provider}

    try:
        with httpx.Client(timeout=_TIMEOUT) as client:
            resp = client.post(f"{_base_url()}/v1/whatsapp/proposals/{id_proposal}/biometry/continue", headers=headers, json=payload)

        body = resp.json() if resp.content else {}
        biometry_status = body.get("status") or body.get("biometryStatus", "")

        if biometry_status == "APPROVED":
            return {"status": "APPROVED", "message": "Biometria aprovada! Prosseguir para aceite formal.", "http_status": resp.status_code, "id_biometric": id_biometric}

        if biometry_status == "BIOMETRICS":
            return {"status": "PENDING", "message": "Biometria em processamento. Aguardar e tentar novamente.", "http_status": resp.status_code}

        if biometry_status == "DENIED":
            return {"status": "DENIED", "message": "Biometria reprovada. Fluxo não pode prosseguir.", "http_status": resp.status_code}

        return {"status": "ERROR", "message": f"Status inesperado '{biometry_status}' (HTTP {resp.status_code}).", "http_status": resp.status_code}

    except RuntimeError as exc:
        return {"status": "ERROR", "message": str(exc), "http_status": None}
    except httpx.TimeoutException:
        return {"status": "ERROR", "message": "Timeout ao consultar biometria.", "http_status": None}
    except httpx.RequestError as exc:
        return {"status": "ERROR", "message": f"Erro de conexão: {exc}", "http_status": None}
