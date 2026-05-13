"""Simula o fluxo completo de contratação sem WhatsApp real.

Envia mensagens para o agente local e dispara os webhooks banQi
que normalmente chegariam de forma assíncrona.

Uso:
  python scripts/simulate_flow.py

Pré-requisitos:
  - docker-compose up (mock-api + dynamodb + agent)
  - .env com AWS_PROFILE configurado (para Bedrock)
"""

from __future__ import annotations

import json
import time

import httpx

AGENT_URL = "http://localhost:8080"
MOCK_URL = "http://localhost:8000"
PHONE = "+5511999990001"
CPF = "12345678900"


def send_message(text: str) -> str:
    """Envia mensagem simulando o WhatsApp e retorna resposta do agente."""
    payload = {
        "object": "whatsapp_business_account",
        "entry": [{
            "id": "123",
            "changes": [{
                "value": {
                    "messaging_product": "whatsapp",
                    "messages": [{
                        "id": f"msg_{int(time.time()*1000)}",
                        "from": PHONE,
                        "type": "text",
                        "text": {"body": text},
                        "timestamp": str(int(time.time())),
                    }]
                },
                "field": "messages"
            }]
        }]
    }

    # Assinatura fake — ok em dev (APP_SECRET vazio ignora validação)
    resp = httpx.post(
        f"{AGENT_URL}/whatsapp",
        content=json.dumps(payload).encode(),
        headers={
            "Content-Type": "application/json",
            "X-Hub-Signature-256": "sha256=fake",
        },
        timeout=30,
    )
    return resp.text


def fire_webhook(event: str, data: dict) -> None:
    """Dispara um webhook banQi para o agente local."""
    payload = {"event": event, "phone": PHONE, **data}
    resp = httpx.post(
        f"{AGENT_URL}/webhook/banqi",
        json=payload,
        timeout=10,
    )
    print(f"  webhook {event} → {resp.status_code}")


def wait(msg: str, seconds: int = 1) -> None:
    print(f"\n⏳ {msg}")
    time.sleep(seconds)


def main() -> None:
    print("=" * 60)
    print("Simulação do fluxo completo — banQi Consignado")
    print("=" * 60)

    print("\n[Etapa 1] Cliente inicia contato")
    r = send_message("Oi, quero fazer um empréstimo consignado")
    print(f"Agente: {r[:200]}")

    wait("Enviando CPF...")
    r = send_message(CPF)
    print(f"Agente: {r[:200]}")

    wait("Enviando nome...")
    r = send_message("João da Silva")
    print(f"Agente: {r[:200]}")

    wait("Disparando webhook CONSENT_TERM_FILE_READY...", 2)
    fire_webhook("CONSENT_TERM_FILE_READY", {
        "pdfUrl": "https://mock.banqi.com.br/termo/12345.pdf"
    })

    wait("Cliente aceita o termo...")
    r = send_message("Sim, aceito os termos")
    print(f"Agente: {r[:200]}")

    wait("Disparando webhook SIMULATION_READY...", 2)
    fire_webhook("SIMULATION_READY", {
        "data": {
            "simulations": [{
                "amount": 5000.00,
                "numInstallments": 24,
                "installmentAmount": 245.50,
                "monthlyRate": 1.89,
                "disbursementDate": "2026-05-20",
            }]
        }
    })

    wait("Cliente aceita simulação...")
    r = send_message("Quero prosseguir com esses valores")
    print(f"Agente: {r[:200]}")

    wait("Coletando dados — e-mail...")
    r = send_message("joao.silva@email.com")
    print(f"Agente: {r[:200]}")

    wait("Disparando webhook PROPOSAL_CREATED...", 3)
    fire_webhook("PROPOSAL_CREATED", {
        "idProposal": "prop-uuid-12345"
    })

    wait("Simulando aprovação final...")
    fire_webhook("PROPOSAL_STATUS_UPDATE", {"newStatus": "SIGNED"})
    time.sleep(1)
    fire_webhook("PROPOSAL_STATUS_UPDATE", {"newStatus": "CCB_GENERATED"})
    time.sleep(1)
    fire_webhook("PROPOSAL_STATUS_UPDATE", {"newStatus": "DISBURSED", "amount": "5000.00"})

    print("\n✅ Simulação concluída!")
    print("Verifique os logs do agente para o fluxo completo.")


if __name__ == "__main__":
    main()
