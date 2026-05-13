"""Tools de simulação de empréstimo consignado — etapa 2 do fluxo.

create_simulation: cria ou recupera simulação (síncrono 200 ou assíncrono 202).
get_simulations: busca simulações existentes (fallback quando webhook é perdido).
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
def create_simulation(
    phone: str,
    cpf: str,
    amount: float | None = None,
    num_installments: list[int] | None = None,
) -> dict[str, Any]:
    """Cria uma simulação de empréstimo consignado para o cliente.

    Sem amount e num_installments → simulação automática com a melhor oferta disponível.
    Com amount e/ou num_installments → simulação personalizada pelos valores informados.

    Args:
        phone: Telefone do cliente em formato E.164.
        cpf: CPF do cliente com 11 dígitos, sem formatação.
        amount: Valor desejado do empréstimo em reais (opcional).
        num_installments: Lista com os números de parcelas desejados, ex: [12, 24, 36] (opcional).

    Returns:
        dict com status: "READY" | "WAITING" | "TOKEN_EXPIRED" | "ERROR"
    """
    headers = _make_headers(phone, cpf)
    payload: dict[str, Any] | None = None
    if amount is not None or num_installments is not None:
        payload = {}
        if amount is not None:
            payload["amount"] = amount
        if num_installments is not None:
            payload["numInstallments"] = num_installments

    try:
        with httpx.Client(timeout=_TIMEOUT) as client:
            resp = client.post(
                f"{_base_url()}/v1/whatsapp/simulations",
                headers=headers,
                json=payload,
            )

        if resp.status_code == 200:
            body = resp.json() if resp.content else {}
            return {
                "status": "READY",
                "message": "Simulação disponível imediatamente.",
                "http_status": 200,
                "simulations": body.get("simulations", body.get("data", [body])),
            }

        if resp.status_code == 202:
            body = resp.json() if resp.content else {}
            return {
                "status": "WAITING",
                "message": "Simulação sendo processada. Aguardando webhook SIMULATION_COMPLETED.",
                "http_status": 202,
                "id_correlation": body.get("idCorrelation"),
            }

        if resp.status_code == 422:
            body = resp.json() if resp.content else {}
            error_code = body.get("errorCode", "")
            if "token" in str(error_code).lower():
                return {"status": "TOKEN_EXPIRED", "message": "Token expirado. Cliente precisa reiniciar o fluxo.", "http_status": 422}
            return {"status": "ERROR", "message": f"Erro de validação (HTTP 422): {body}", "http_status": 422}

        return {"status": "ERROR", "message": f"Erro inesperado (HTTP {resp.status_code}).", "http_status": resp.status_code}

    except RuntimeError as exc:
        return {"status": "ERROR", "message": str(exc), "http_status": None}
    except httpx.TimeoutException:
        return {"status": "ERROR", "message": "Timeout ao conectar com a API banQi.", "http_status": None}
    except httpx.RequestError as exc:
        return {"status": "ERROR", "message": f"Erro de conexão: {exc}", "http_status": None}


@tool
def get_simulations(
    phone: str,
    cpf: str,
    id_correlation: str | None = None,
) -> dict[str, Any]:
    """Busca simulações existentes para o cliente (fallback quando webhook SIMULATION_COMPLETED é perdido).

    Args:
        phone: Telefone do cliente em formato E.164.
        cpf: CPF do cliente com 11 dígitos, sem formatação.
        id_correlation: ID de correlação retornado em create_simulation (opcional).

    Returns:
        dict com status: "FOUND" | "NOT_FOUND" | "ERROR"
    """
    headers = _make_headers(phone, cpf)
    headers.pop("Content-Type", None)
    params: dict[str, str] = {}
    if id_correlation:
        params["idCorrelation"] = id_correlation

    try:
        with httpx.Client(timeout=_TIMEOUT) as client:
            resp = client.get(
                f"{_base_url()}/v1/whatsapp/simulations",
                headers=headers,
                params=params if params else None,
            )

        if resp.status_code == 200:
            body = resp.json() if resp.content else {}
            simulations = body.get("simulations", body.get("data", []))
            if not simulations and isinstance(body, list):
                simulations = body
            if simulations:
                return {"status": "FOUND", "message": f"Encontrada(s) {len(simulations)} simulação(ões).", "http_status": 200, "simulations": simulations}
            return {"status": "NOT_FOUND", "message": "Nenhuma simulação encontrada.", "http_status": 200, "simulations": []}

        if resp.status_code == 404:
            return {"status": "NOT_FOUND", "message": "Nenhuma simulação encontrada.", "http_status": 404, "simulations": []}

        return {"status": "ERROR", "message": f"Erro ao buscar simulações (HTTP {resp.status_code}).", "http_status": resp.status_code}

    except RuntimeError as exc:
        return {"status": "ERROR", "message": str(exc), "http_status": None}
    except httpx.TimeoutException:
        return {"status": "ERROR", "message": "Timeout ao conectar com a API banQi.", "http_status": None}
    except httpx.RequestError as exc:
        return {"status": "ERROR", "message": f"Erro de conexão: {exc}", "http_status": None}
