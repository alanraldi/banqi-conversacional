"""Tools para gerenciamento de termo de consentimento — etapas 1 e 2 do fluxo.

create_consent_term: cria o termo (assíncrono, aguarda webhook CONSENT_TERM_FILE_READY).
accept_consent_term: aceita o termo (assíncrono, aguarda webhook SIMULATION_READY ou NO_OFFER_AVAILABLE).
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
    """Monta os headers obrigatórios para todas as chamadas banQi."""
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
def create_consent_term(name: str, phone: str, cpf: str) -> dict[str, Any]:
    """Cria o termo de consentimento para o cliente iniciar o fluxo de empréstimo consignado.

    Envia o nome do cliente para a API banQi gerar o PDF do termo de consentimento.
    O processamento é assíncrono: a resposta 202 indica que o PDF será entregue via
    webhook CONSENT_TERM_FILE_READY. Aguardar o webhook antes de prosseguir.

    Args:
        name: Nome completo do cliente.
        phone: Telefone do cliente em formato E.164 (ex: +5511999999999).
        cpf: CPF do cliente com 11 dígitos, sem formatação.

    Returns:
        dict com campos:
        - status: "PENDING" (aguardando webhook) | "ALREADY_ACTIVE" (termo já existe) |
                  "TOO_MANY_CPFS" (3+ CPFs no telefone) | "ERROR"
        - message: Descrição legível do resultado.
        - http_status: Código HTTP retornado pela API.
    """
    headers = _make_headers(phone, cpf)
    payload = {"name": name}

    try:
        with httpx.Client(timeout=_TIMEOUT) as client:
            resp = client.post(
                f"{_base_url()}/v1/whatsapp/consent-term",
                headers=headers,
                json=payload,
            )

        logger.info(
            "create_consent_term: http_status=%s phone=%s",
            resp.status_code,
            phone[:6] + "****",
        )

        if resp.status_code == 202:
            return {
                "status": "PENDING",
                "message": "Termo de consentimento sendo gerado. Aguardando webhook CONSENT_TERM_FILE_READY.",
                "http_status": 202,
            }

        if resp.status_code == 406:
            return {
                "status": "TOO_MANY_CPFS",
                "message": "Este número de telefone já possui 3 ou mais CPFs associados. Não é possível prosseguir.",
                "http_status": 406,
            }

        if resp.status_code == 409:
            return {
                "status": "ALREADY_ACTIVE",
                "message": "Já existe um termo de consentimento ativo para este cliente. Prosseguir para aceitação.",
                "http_status": 409,
            }

        # Outros erros inesperados
        try:
            body = resp.json()
        except Exception:
            body = resp.text

        logger.error("create_consent_term: resposta inesperada %s body=%s", resp.status_code, body)
        return {
            "status": "ERROR",
            "message": f"Erro inesperado ao criar termo de consentimento (HTTP {resp.status_code}).",
            "http_status": resp.status_code,
            "detail": body,
        }

    except RuntimeError as exc:
        logger.error("create_consent_term: configuração inválida — %s", exc)
        return {
            "status": "ERROR",
            "message": str(exc),
            "http_status": None,
        }
    except httpx.TimeoutException:
        logger.error("create_consent_term: timeout ao chamar API banQi")
        return {
            "status": "ERROR",
            "message": "Timeout ao conectar com a API banQi. Tente novamente.",
            "http_status": None,
        }
    except httpx.RequestError as exc:
        logger.error("create_consent_term: erro de rede — %s", exc)
        return {
            "status": "ERROR",
            "message": f"Erro de conexão com a API banQi: {exc}",
            "http_status": None,
        }


@tool
def accept_consent_term(phone: str, cpf: str, ip: str, user_agent: str) -> dict[str, Any]:
    """Registra a aceitação do termo de consentimento pelo cliente.

    Deve ser chamado após o cliente confirmar que leu e aceita o termo de consentimento.
    O processamento é assíncrono: aguardar webhook SIMULATION_READY (oferta disponível)
    ou NO_OFFER_AVAILABLE (cliente não tem oferta de crédito consignado).

    Args:
        phone: Telefone do cliente em formato E.164.
        cpf: CPF do cliente com 11 dígitos, sem formatação.
        ip: Endereço IP do cliente (obtido do contexto da sessão WhatsApp).
        user_agent: User-Agent do cliente (obtido do contexto da sessão WhatsApp).

    Returns:
        dict com campos:
        - status: "ACCEPTED" (aceito, aguardando simulação) | "ERROR"
        - message: Descrição legível do resultado.
        - http_status: Código HTTP retornado pela API.
    """
    headers = _make_headers(phone, cpf)
    payload = {"ip": ip, "userAgent": user_agent}

    try:
        with httpx.Client(timeout=_TIMEOUT) as client:
            resp = client.post(
                f"{_base_url()}/v1/whatsapp/consent-term/accept",
                headers=headers,
                json=payload,
            )

        logger.info(
            "accept_consent_term: http_status=%s phone=%s",
            resp.status_code,
            phone[:6] + "****",
        )

        if resp.status_code == 200:
            return {
                "status": "ACCEPTED",
                "message": (
                    "Termo de consentimento aceito com sucesso. "
                    "Aguardando webhook SIMULATION_READY ou NO_OFFER_AVAILABLE."
                ),
                "http_status": 200,
            }

        try:
            body = resp.json()
        except Exception:
            body = resp.text

        logger.error("accept_consent_term: resposta inesperada %s body=%s", resp.status_code, body)
        return {
            "status": "ERROR",
            "message": f"Erro ao aceitar termo de consentimento (HTTP {resp.status_code}).",
            "http_status": resp.status_code,
            "detail": body,
        }

    except RuntimeError as exc:
        logger.error("accept_consent_term: configuração inválida — %s", exc)
        return {
            "status": "ERROR",
            "message": str(exc),
            "http_status": None,
        }
    except httpx.TimeoutException:
        logger.error("accept_consent_term: timeout ao chamar API banQi")
        return {
            "status": "ERROR",
            "message": "Timeout ao conectar com a API banQi. Tente novamente.",
            "http_status": None,
        }
    except httpx.RequestError as exc:
        logger.error("accept_consent_term: erro de rede — %s", exc)
        return {
            "status": "ERROR",
            "message": f"Erro de conexão com a API banQi: {exc}",
            "http_status": None,
        }
