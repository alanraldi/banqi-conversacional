"""Tools de simulação de empréstimo consignado — etapa 3 do fluxo.

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

    Retorno 200: simulação já disponível (cache hit) → status READY com dados imediatos.
    Retorno 202: simulação sendo processada → status WAITING, aguardar webhook SIMULATION_COMPLETED.
    Erro 422 TOKEN_EXPIRED: o token de acesso expirou, cliente precisa reiniciar o fluxo.

    Args:
        phone: Telefone do cliente em formato E.164.
        cpf: CPF do cliente com 11 dígitos, sem formatação.
        amount: Valor desejado do empréstimo em reais (opcional).
        num_installments: Lista com os números de parcelas desejados, ex: [12, 24, 36] (opcional).

    Returns:
        dict com campos:
        - status: "READY" | "WAITING" | "TOKEN_EXPIRED" | "ERROR"
        - message: Descrição legível do resultado.
        - http_status: Código HTTP retornado pela API.
        - simulations: Lista de simulações (somente quando status="READY").
        - id_correlation: ID de correlação para rastreamento (quando disponível).
    """
    headers = _make_headers(phone, cpf)

    # Monta body apenas se houver parâmetros explícitos
    payload: dict[str, Any] | None = None
    if amount is not None or num_installments is not None:
        payload = {}
        if amount is not None:
            payload["amount"] = amount
        if num_installments is not None:
            payload["numInstallments"] = num_installments

    try:
        with httpx.Client(timeout=_TIMEOUT) as client:
            if payload is not None:
                resp = client.post(
                    f"{_base_url()}/v1/whatsapp/simulations",
                    headers=headers,
                    json=payload,
                )
            else:
                resp = client.post(
                    f"{_base_url()}/v1/whatsapp/simulations",
                    headers=headers,
                )

        logger.info(
            "create_simulation: http_status=%s phone=%s amount=%s",
            resp.status_code,
            phone[:6] + "****",
            amount,
        )

        if resp.status_code == 200:
            try:
                body = resp.json()
            except Exception:
                body = {}
            return {
                "status": "READY",
                "message": "Simulação disponível imediatamente (cache hit).",
                "http_status": 200,
                "simulations": body.get("simulations", body.get("data", [body])),
                "id_correlation": body.get("idCorrelation"),
            }

        if resp.status_code == 202:
            try:
                body = resp.json()
            except Exception:
                body = {}
            return {
                "status": "WAITING",
                "message": "Simulação sendo processada. Aguardando webhook SIMULATION_COMPLETED.",
                "http_status": 202,
                "id_correlation": body.get("idCorrelation"),
            }

        if resp.status_code == 422:
            try:
                body = resp.json()
            except Exception:
                body = {}
            error_code = body.get("errorCode", body.get("code", ""))
            if error_code == "TOKEN_EXPIRED" or "token" in str(error_code).lower():
                logger.warning("create_simulation: token expirado para phone=%s", phone[:6] + "****")
                return {
                    "status": "TOKEN_EXPIRED",
                    "message": (
                        "O token de acesso expirou. O cliente precisa reiniciar o fluxo "
                        "de consentimento para obter um novo token."
                    ),
                    "http_status": 422,
                    "error_code": error_code,
                }
            return {
                "status": "ERROR",
                "message": f"Erro de validação ao criar simulação (HTTP 422): {body}",
                "http_status": 422,
                "detail": body,
            }

        try:
            body = resp.json()
        except Exception:
            body = resp.text

        logger.error("create_simulation: resposta inesperada %s body=%s", resp.status_code, body)
        return {
            "status": "ERROR",
            "message": f"Erro inesperado ao criar simulação (HTTP {resp.status_code}).",
            "http_status": resp.status_code,
            "detail": body,
        }

    except RuntimeError as exc:
        logger.error("create_simulation: configuração inválida — %s", exc)
        return {"status": "ERROR", "message": str(exc), "http_status": None}
    except httpx.TimeoutException:
        logger.error("create_simulation: timeout ao chamar API banQi")
        return {
            "status": "ERROR",
            "message": "Timeout ao conectar com a API banQi. Tente novamente.",
            "http_status": None,
        }
    except httpx.RequestError as exc:
        logger.error("create_simulation: erro de rede — %s", exc)
        return {
            "status": "ERROR",
            "message": f"Erro de conexão com a API banQi: {exc}",
            "http_status": None,
        }


@tool
def get_simulations(
    phone: str,
    cpf: str,
    id_correlation: str | None = None,
) -> dict[str, Any]:
    """Busca simulações existentes para o cliente (fallback quando webhook SIMULATION_COMPLETED é perdido).

    Deve ser usado como alternativa quando o webhook não foi recebido em tempo hábil.
    O idCorrelation pode ser usado para buscar uma simulação específica.

    Args:
        phone: Telefone do cliente em formato E.164.
        cpf: CPF do cliente com 11 dígitos, sem formatação.
        id_correlation: ID de correlação retornado em create_simulation (opcional).

    Returns:
        dict com campos:
        - status: "FOUND" | "NOT_FOUND" | "ERROR"
        - message: Descrição legível do resultado.
        - http_status: Código HTTP retornado pela API.
        - simulations: Lista de simulações disponíveis (quando status="FOUND").
    """
    headers = _make_headers(phone, cpf)
    # Remove Content-Type para GET
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

        logger.info(
            "get_simulations: http_status=%s phone=%s id_correlation=%s",
            resp.status_code,
            phone[:6] + "****",
            id_correlation,
        )

        if resp.status_code == 200:
            try:
                body = resp.json()
            except Exception:
                body = {}
            simulations = body.get("simulations", body.get("data", []))
            if not simulations and isinstance(body, list):
                simulations = body

            if simulations:
                return {
                    "status": "FOUND",
                    "message": f"Encontrada(s) {len(simulations)} simulação(ões) disponível(is).",
                    "http_status": 200,
                    "simulations": simulations,
                }
            return {
                "status": "NOT_FOUND",
                "message": "Nenhuma simulação encontrada para este cliente no momento.",
                "http_status": 200,
                "simulations": [],
            }

        if resp.status_code == 404:
            return {
                "status": "NOT_FOUND",
                "message": "Nenhuma simulação encontrada. O cliente pode precisar criar uma nova simulação.",
                "http_status": 404,
                "simulations": [],
            }

        try:
            body = resp.json()
        except Exception:
            body = resp.text

        logger.error("get_simulations: resposta inesperada %s body=%s", resp.status_code, body)
        return {
            "status": "ERROR",
            "message": f"Erro ao buscar simulações (HTTP {resp.status_code}).",
            "http_status": resp.status_code,
            "detail": body,
        }

    except RuntimeError as exc:
        logger.error("get_simulations: configuração inválida — %s", exc)
        return {"status": "ERROR", "message": str(exc), "http_status": None}
    except httpx.TimeoutException:
        logger.error("get_simulations: timeout ao chamar API banQi")
        return {
            "status": "ERROR",
            "message": "Timeout ao conectar com a API banQi. Tente novamente.",
            "http_status": None,
        }
    except httpx.RequestError as exc:
        logger.error("get_simulations: erro de rede — %s", exc)
        return {
            "status": "ERROR",
            "message": f"Erro de conexão com a API banQi: {exc}",
            "http_status": None,
        }
