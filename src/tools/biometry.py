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

    Envia o ID da proposta para a API banQi iniciar o fluxo de biometria via Único.
    Retorna o BioLink que deve ser enviado ao cliente via WhatsApp para ele fazer
    o liveness + face match em seu próprio dispositivo.

    Args:
        phone: Telefone do cliente em formato E.164.
        cpf: CPF do cliente com 11 dígitos, sem formatação.
        id_proposal: UUID da proposta criada na etapa 4.

    Returns:
        dict com campos:
        - status: "STARTED" | "ERROR"
        - message: Descrição legível do resultado.
        - http_status: Código HTTP retornado pela API.
        - bio_link: URL para o cliente fazer a biometria (quando status="STARTED").
        - id_anti_fraud: ID do processo antifraude para usar em continue_biometry.
    """
    headers = _make_headers(phone, cpf)

    try:
        with httpx.Client(timeout=_TIMEOUT) as client:
            resp = client.post(
                f"{_base_url()}/v1/whatsapp/proposals/{id_proposal}/biometry",
                headers=headers,
            )

        logger.info(
            "start_biometry: http_status=%s id_proposal=%s",
            resp.status_code,
            id_proposal,
        )

        if resp.status_code in (200, 201):
            try:
                body = resp.json()
            except Exception:
                body = {}
            return {
                "status": "STARTED",
                "message": "Biometria iniciada. Enviar o BioLink ao cliente para realizar o liveness.",
                "http_status": resp.status_code,
                "bio_link": body.get("bioLink") or body.get("bio_link", ""),
                "id_anti_fraud": body.get("idAntiFraud") or body.get("id_anti_fraud", ""),
            }

        try:
            body = resp.json()
        except Exception:
            body = resp.text

        logger.error("start_biometry: resposta inesperada %s body=%s", resp.status_code, body)
        return {
            "status": "ERROR",
            "message": f"Erro ao iniciar biometria (HTTP {resp.status_code}).",
            "http_status": resp.status_code,
            "detail": body,
        }

    except RuntimeError as exc:
        logger.error("start_biometry: configuração inválida — %s", exc)
        return {"status": "ERROR", "message": str(exc), "http_status": None}
    except httpx.TimeoutException:
        logger.error("start_biometry: timeout ao chamar API banQi")
        return {
            "status": "ERROR",
            "message": "Timeout ao iniciar biometria. Tente novamente.",
            "http_status": None,
        }
    except httpx.RequestError as exc:
        logger.error("start_biometry: erro de rede — %s", exc)
        return {
            "status": "ERROR",
            "message": f"Erro de conexão com a API banQi: {exc}",
            "http_status": None,
        }


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

    Deve ser chamado após o cliente realizar o liveness + face match via BioLink.
    O idBiometric é fornecido pelo SDK do Único após a biometria ser concluída.

    Status possíveis:
    - APPROVED: biometria aprovada, prosseguir para etapa 6 (aceite formal)
    - BIOMETRICS: biometria pendente (liveness ainda em processamento), aguardar e tentar de novo
    - DENIED: biometria reprovada, encerrar fluxo com empatia

    Args:
        phone: Telefone do cliente em formato E.164.
        cpf: CPF do cliente com 11 dígitos, sem formatação.
        id_proposal: UUID da proposta.
        id_anti_fraud: ID antifraude retornado em start_biometry.
        id_biometric: ID da biometria fornecido pelo SDK Único após a captura.
        provider: Provedor da biometria (ex: "UNICO").

    Returns:
        dict com campos:
        - status: "APPROVED" | "PENDING" | "DENIED" | "ERROR"
        - biometry_status: Status original da API ("APPROVED", "BIOMETRICS", "DENIED")
        - message: Descrição legível do resultado.
        - http_status: Código HTTP retornado pela API.
        - id_biometric: ID da biometria aprovada (usar na etapa 6 de aceite).
    """
    headers = _make_headers(phone, cpf)
    payload = {
        "idAntiFraud": id_anti_fraud,
        "idBiometric": id_biometric,
        "provider": provider,
    }

    try:
        with httpx.Client(timeout=_TIMEOUT) as client:
            resp = client.post(
                f"{_base_url()}/v1/whatsapp/proposals/{id_proposal}/biometry/continue",
                headers=headers,
                json=payload,
            )

        logger.info(
            "continue_biometry: http_status=%s id_proposal=%s",
            resp.status_code,
            id_proposal,
        )

        try:
            body = resp.json()
        except Exception:
            body = {}

        biometry_status = (
            body.get("status")
            or body.get("biometryStatus")
            or body.get("biometry_status", "")
        )

        if biometry_status == "APPROVED":
            return {
                "status": "APPROVED",
                "biometry_status": "APPROVED",
                "message": "Biometria aprovada! Prosseguir para o aceite formal do contrato.",
                "http_status": resp.status_code,
                "id_biometric": id_biometric,
            }

        if biometry_status == "BIOMETRICS":
            return {
                "status": "PENDING",
                "biometry_status": "BIOMETRICS",
                "message": (
                    "Biometria ainda em processamento. "
                    "Aguardar alguns instantes e tentar novamente."
                ),
                "http_status": resp.status_code,
                "id_biometric": id_biometric,
            }

        if biometry_status == "DENIED":
            return {
                "status": "DENIED",
                "biometry_status": "DENIED",
                "message": (
                    "Biometria reprovada. Não foi possível verificar a identidade do cliente. "
                    "O fluxo de contratação não pode prosseguir."
                ),
                "http_status": resp.status_code,
                "id_biometric": id_biometric,
            }

        # Status desconhecido ou erro HTTP
        logger.error(
            "continue_biometry: status inesperado '%s' http=%s body=%s",
            biometry_status,
            resp.status_code,
            body,
        )
        return {
            "status": "ERROR",
            "biometry_status": biometry_status,
            "message": f"Resposta inesperada ao consultar biometria (HTTP {resp.status_code}).",
            "http_status": resp.status_code,
            "detail": body,
        }

    except RuntimeError as exc:
        logger.error("continue_biometry: configuração inválida — %s", exc)
        return {"status": "ERROR", "message": str(exc), "http_status": None}
    except httpx.TimeoutException:
        logger.error("continue_biometry: timeout ao chamar API banQi")
        return {
            "status": "ERROR",
            "message": "Timeout ao consultar biometria. Tente novamente.",
            "http_status": None,
        }
    except httpx.RequestError as exc:
        logger.error("continue_biometry: erro de rede — %s", exc)
        return {
            "status": "ERROR",
            "message": f"Erro de conexão com a API banQi: {exc}",
            "http_status": None,
        }
