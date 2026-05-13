"""
Mock server — banQi Payroll Loan WhatsApp API (Etapas 1-7)
Simula todos os endpoints + disparo assíncrono de webhooks via background tasks.
"""
import asyncio
import uuid
import base64
from datetime import datetime, timedelta, timezone
from typing import Optional

import httpx
from fastapi import FastAPI, Header, BackgroundTasks, HTTPException, Query
from fastapi.responses import JSONResponse
from pydantic import BaseModel

app = FastAPI(title="banQi Mock API", version="1.0.0")

# ─── Estado em memória ────────────────────────────────────────────────────────

# Keyed by phone (E.164)
state: dict[str, dict] = {}

# Webhooks enviados (para verificação nos testes), keyed by phone
webhook_log: dict[str, list[dict]] = {}


def get_user(phone: str) -> dict:
    if phone not in state:
        state[phone] = {"cpf": None, "name": None, "consent_term": None,
                        "simulation": None, "proposal": None}
    return state[phone]


def log_webhook(phone: str, payload: dict):
    webhook_log.setdefault(phone, []).append(payload)


# ─── PDF fake (base64 minimal) ────────────────────────────────────────────────

FAKE_PDF_B64 = base64.b64encode(b"%PDF-1.4 mock consent term PDF banQi").decode()


# ─── Helpers de webhook ───────────────────────────────────────────────────────

async def send_webhook(phone: str, payload: dict, delay: float = 0.8):
    await asyncio.sleep(delay)
    log_webhook(phone, payload)


# ─── Etapa 1: Termo de Consentimento ─────────────────────────────────────────

class ConsentTermRequest(BaseModel):
    name: str


@app.post("/v1/whatsapp/consent-term", status_code=202)
async def create_consent_term(
    body: ConsentTermRequest,
    background_tasks: BackgroundTasks,
    x_whatsapp_phone: str = Header(...),
    x_document: str = Header(...),
    x_partner: str = Header(...),
):
    user = get_user(x_whatsapp_phone)

    # 406 — Limite de CPFs vinculados ao telefone
    linked = [p for p, u in state.items() if p != x_whatsapp_phone and u.get("cpf") == x_document]
    if len(linked) >= 3:
        raise HTTPException(406, detail="Limite de CPFs vinculados ao número atingido. Máximo permitido: 3.")

    # 409 — Já possui termo ativo
    if user["consent_term"] and user["consent_term"]["status"] == "TOKEN_GENERATED":
        raise HTTPException(409, detail="Usuário já possui um termo de consentimento ativo")

    user["cpf"] = x_document
    user["name"] = body.name
    id_correlation = f"ct-{uuid.uuid4().hex[:8]}"
    expiration_at = (datetime.now(timezone.utc) + timedelta(hours=48)).isoformat()

    user["consent_term"] = {
        "status": "CREATED",
        "id_correlation": id_correlation,
        "expiration_at": expiration_at,
    }

    # CPF especial para simular falha: CPF começando com "999"
    if x_document.startswith("999"):
        webhook_payload = {
            "event": "NO_OFFER_AVAILABLE",
            "phone": x_whatsapp_phone,
            "idCorrelation": id_correlation,
            "errorCode": "PDF_GENERATION_ERROR",
            "reason": "Falha na geração do PDF do termo de consentimento",
        }
    else:
        webhook_payload = {
            "event": "CONSENT_TERM_FILE_READY",
            "phone": x_whatsapp_phone,
            "idCorrelation": id_correlation,
            "consentTerm": {
                "status": "CREATED",
                "pdf": FAKE_PDF_B64,
                "expirationAt": expiration_at,
            },
        }

    background_tasks.add_task(send_webhook, x_whatsapp_phone, webhook_payload)
    return {"status": "GENERATING", "message": "Termo de consentimento sendo gerado."}


# ─── Etapa 2: Aceite + Simulação Automática ───────────────────────────────────

class AcceptConsentTermRequest(BaseModel):
    ip: str
    userAgent: Optional[str] = "WhatsApp/2.23.0"


@app.post("/v1/whatsapp/consent-term/accept")
async def accept_consent_term(
    body: AcceptConsentTermRequest,
    background_tasks: BackgroundTasks,
    x_whatsapp_phone: str = Header(...),
    x_document: str = Header(...),
    x_partner: str = Header(...),
):
    user = get_user(x_whatsapp_phone)
    ct = user.get("consent_term")

    if not ct:
        raise HTTPException(404, detail="Termo de consentimento não encontrado")
    if ct["status"] == "TOKEN_GENERATED":
        raise HTTPException(409, detail="Termo de consentimento já foi aceito")
    if ct["status"] != "CREATED":
        raise HTTPException(422, detail="Termo de consentimento expirado. Solicite novo termo.")

    ct["status"] = "TOKEN_GENERATED"
    id_correlation = f"sim-auto-{uuid.uuid4().hex[:8]}"
    id_simulation = str(uuid.uuid4())

    # CPF começando com "000" → sem elegibilidade
    if x_document.startswith("000"):
        webhook_payload = {
            "event": "NO_OFFER_AVAILABLE",
            "phone": x_whatsapp_phone,
            "idCorrelation": id_correlation,
            "errorCode": "ELIGIBILITY_REJECTED",
            "reason": "Margem insuficiente para concessão de crédito",
        }
        background_tasks.add_task(send_webhook, x_whatsapp_phone, webhook_payload)
    else:
        sim_data = _build_simulation_data(8000.0, 24)
        user["simulation"] = {
            "id_simulation": id_simulation,
            "amount": 8000.0,
            "num_installments": 24,
            "status": "SUCCESS",
            "data": sim_data,
        }
        webhook_payload = {
            "event": "SIMULATION_READY",
            "phone": x_whatsapp_phone,
            "idCorrelation": id_correlation,
            "simulation": {
                "status": "SUCCESS",
                "simulations": [{
                    "idSimulation": id_simulation,
                    "amount": 8000.0,
                    "numInstallments": 24,
                    "simulationData": sim_data,
                }],
            },
        }
        background_tasks.add_task(send_webhook, x_whatsapp_phone, webhook_payload)

    return {
        "status": "GENERATING_TOKEN",
        "message": "Aceite registrado. Simulação automática será disparada.",
        "simulationTriggered": True,
    }


# ─── Etapa 3: Simulação Manual ────────────────────────────────────────────────

class SimulationRequest(BaseModel):
    amount: Optional[float] = None
    numInstallments: Optional[list[int]] = None


@app.post("/v1/whatsapp/simulations")
async def create_simulation(
    body: SimulationRequest,
    background_tasks: BackgroundTasks,
    x_whatsapp_phone: str = Header(...),
    x_document: str = Header(...),
    x_partner: str = Header(...),
):
    user = get_user(x_whatsapp_phone)
    ct = user.get("consent_term")

    if not ct:
        raise HTTPException(422, detail={"errorCode": "CONSENT_TERM_NOT_FOUND",
                                          "message": "Nenhum termo encontrado"})
    if ct["status"] != "TOKEN_GENERATED":
        raise HTTPException(422, detail={"errorCode": "CONSENT_TERM_INVALID_STATUS",
                                          "message": "Termo não aceito ainda"})

    amount = body.amount or 8000.0
    installments = body.numInstallments[0] if body.numInstallments else 24
    id_correlation = f"sim-{uuid.uuid4().hex[:8]}"
    id_simulation = str(uuid.uuid4())

    existing = user.get("simulation")
    # Cache hit: mesmos parâmetros
    if (existing and existing["status"] == "SUCCESS"
            and existing["amount"] == amount
            and existing["num_installments"] == installments):
        return {
            "idCorrelation": id_correlation,
            "status": "SUCCESS",
            "simulations": [{
                "idSimulation": existing["id_simulation"],
                "amount": existing["amount"],
                "numInstallments": existing["num_installments"],
                "simulationData": existing["data"],
            }],
        }

    # Cache miss → assíncrono
    sim_data = _build_simulation_data(amount, installments)
    user["simulation"] = {
        "id_simulation": id_simulation,
        "amount": amount,
        "num_installments": installments,
        "status": "SUCCESS",
        "data": sim_data,
    }

    webhook_payload = {
        "event": "SIMULATION_COMPLETED",
        "phone": x_whatsapp_phone,
        "idCorrelation": id_correlation,
        "simulation": {
            "status": "SUCCESS",
            "simulations": [{
                "idSimulation": id_simulation,
                "amount": amount,
                "numInstallments": installments,
                "simulationData": sim_data,
            }],
        },
    }
    background_tasks.add_task(send_webhook, x_whatsapp_phone, webhook_payload)
    return JSONResponse(
        status_code=202,
        content={"idCorrelation": id_correlation, "status": "WAITING",
                 "message": "Simulação em processamento. Aguarde o webhook SIMULATION_COMPLETED."},
    )


@app.get("/v1/whatsapp/simulations")
async def get_simulations(
    x_whatsapp_phone: str = Header(...),
    x_document: str = Header(...),
    x_partner: str = Header(...),
    idCorrelation: Optional[str] = Query(None),
):
    user = get_user(x_whatsapp_phone)
    sim = user.get("simulation")
    if not sim:
        return None  # 204
    return {
        "simulations": [{
            "idSimulation": sim["id_simulation"],
            "amount": sim["amount"],
            "numInstallments": sim["num_installments"],
            "status": sim["status"],
            "simulationData": sim["data"],
        }]
    }


# ─── Etapa 4: Proposta ────────────────────────────────────────────────────────

class AddressModel(BaseModel):
    street: str
    number: Optional[str] = None
    complement: Optional[str] = None
    neighborhood: str
    city: str
    state: str
    country: str
    zipCode: str


class BankAccountModel(BaseModel):
    bankCode: str
    bankBranch: str
    bankAccount: str
    bankAccountDigit: str
    bankAccountType: str
    ispbCode: Optional[str] = None


class ProposalRequest(BaseModel):
    idSimulation: str
    email: str
    address: AddressModel
    bankAccount: BankAccountModel


@app.post("/v1/whatsapp/proposals", status_code=202)
async def create_proposal(
    body: ProposalRequest,
    background_tasks: BackgroundTasks,
    x_whatsapp_phone: str = Header(...),
    x_document: str = Header(...),
    x_partner: str = Header(...),
):
    user = get_user(x_whatsapp_phone)
    sim = user.get("simulation")

    if not sim or sim["status"] != "SUCCESS":
        raise HTTPException(412, detail="Simulação não encontrada ou não concluída")
    if sim["id_simulation"] != body.idSimulation:
        raise HTTPException(412, detail="idSimulation não corresponde à simulação ativa")

    id_proposal = str(uuid.uuid4())
    user["proposal"] = {
        "id_proposal": id_proposal,
        "status": "CREATED",
        "email": body.email,
        "address": body.address.model_dump(),
        "bank_account": body.bankAccount.model_dump(),
        "biometry": None,
        "accepted": False,
    }

    webhook_payload = {
        "event": "PROPOSAL_CREATED",
        "phone": x_whatsapp_phone,
        "idCorrelation": id_proposal,
        "proposal": {"idProposal": id_proposal, "status": "CREATED"},
    }
    background_tasks.add_task(send_webhook, x_whatsapp_phone, webhook_payload)
    return {"idProposal": id_proposal, "idCorrelation": id_proposal, "status": "CREATED"}


# ─── Etapa 5: Biometria ───────────────────────────────────────────────────────

@app.post("/v1/whatsapp/proposals/{id_proposal}/biometry", status_code=201)
async def start_biometry(
    id_proposal: str,
    x_whatsapp_phone: str = Header(...),
    x_document: str = Header(...),
    x_partner: str = Header(...),
):
    user = get_user(x_whatsapp_phone)
    proposal = user.get("proposal")

    if not proposal or proposal["id_proposal"] != id_proposal:
        raise HTTPException(404, detail="Proposta não encontrada")

    id_anti_fraud = str(uuid.uuid4())
    proposal["biometry"] = {"id_anti_fraud": id_anti_fraud, "status": "BIOMETRICS",
                             "provider": "unico"}
    return {"idAntiFraud": id_anti_fraud, "provider": "unico", "status": "BIOMETRICS"}


class ContinueBiometryRequest(BaseModel):
    idAntiFraud: str
    idBiometric: str
    provider: str


@app.post("/v1/whatsapp/proposals/{id_proposal}/biometry/continue")
async def continue_biometry(
    id_proposal: str,
    body: ContinueBiometryRequest,
    x_whatsapp_phone: str = Header(...),
    x_document: str = Header(...),
    x_partner: str = Header(...),
):
    user = get_user(x_whatsapp_phone)
    proposal = user.get("proposal")

    if not proposal or proposal["id_proposal"] != id_proposal:
        raise HTTPException(404, detail="Proposta não encontrada")

    bio = proposal.get("biometry")
    if not bio or bio["id_anti_fraud"] != body.idAntiFraud:
        raise HTTPException(404, detail="Biometry not found for the given 'idAntiFraud'")

    # idBiometric começando com "denied" simula reprovação
    if body.idBiometric.startswith("denied"):
        status = "DENIED"
    else:
        status = "APPROVED"

    bio["status"] = status
    bio["id_biometric"] = body.idBiometric
    return {"idAntiFraud": body.idAntiFraud, "provider": body.provider, "status": status}


# ─── Etapa 6: Aceite da Proposta ──────────────────────────────────────────────

class AcceptProposalRequest(BaseModel):
    idBiometric: str


@app.post("/v1/whatsapp/proposals/{id_proposal}/accept")
async def accept_proposal(
    id_proposal: str,
    body: AcceptProposalRequest,
    background_tasks: BackgroundTasks,
    x_whatsapp_phone: str = Header(...),
    x_document: str = Header(...),
    x_partner: str = Header(...),
    x_remote_address: str = Header(...),
    user_agent: str = Header(...),
):
    user = get_user(x_whatsapp_phone)
    proposal = user.get("proposal")

    if not proposal or proposal["id_proposal"] != id_proposal:
        raise HTTPException(404, detail="Proposta não encontrada")

    bio = proposal.get("biometry")
    if not bio or bio.get("status") != "APPROVED":
        raise HTTPException(422, detail="Biometria não aprovada")

    proposal["status"] = "ACCEPTED"
    proposal["accepted"] = True
    sim = user["simulation"]

    # Simula ciclo completo de status com delays crescentes
    statuses = ["ACCEPTED", "SIGNED", "CCB_GENERATED", "FORMALIZED",
                "PENDING_DISBURSEMENT", "DISBURSED"]

    for i, new_status in enumerate(statuses):
        payload = {
            "event": "PROPOSAL_STATUS_UPDATE",
            "phone": x_whatsapp_phone,
            "idCorrelation": id_proposal,
            "proposal": {
                "idProposal": id_proposal,
                "status": new_status,
                "newStatus": new_status,
                "disbursementAmount": sim["amount"],
                "disbursementDate": "2026-06-01",
                "paymentAmount": sim["data"]["paymentAmount"],
                "numPeriods": sim["num_installments"],
            },
        }
        background_tasks.add_task(send_webhook, x_whatsapp_phone, payload, delay=0.5 + i * 0.4)

    return {}


# ─── Endpoints de teste ───────────────────────────────────────────────────────

@app.get("/test/webhooks/{phone:path}")
async def get_webhooks(phone: str):
    """Retorna todos os webhooks enviados para um telefone (para verificação nos testes)."""
    return {"phone": phone, "events": webhook_log.get(phone, [])}


@app.delete("/test/webhooks/{phone:path}")
async def clear_webhooks(phone: str):
    """Limpa o log de webhooks de um telefone."""
    webhook_log.pop(phone, None)
    return {"cleared": True}


@app.delete("/test/state/{phone:path}")
async def clear_state(phone: str):
    """Reseta o estado de um usuário (para rodar testes isolados)."""
    state.pop(phone, None)
    webhook_log.pop(phone, None)
    return {"cleared": True}


@app.get("/test/state/{phone:path}")
async def get_state(phone: str):
    """Retorna o estado atual de um usuário."""
    return state.get(phone, {})


# ─── Helpers ──────────────────────────────────────────────────────────────────

def _build_simulation_data(amount: float, installments: int) -> dict:
    monthly_rate = 0.0199
    financed = round(amount * 1.1, 2)
    payment = round(financed * (monthly_rate * (1 + monthly_rate) ** installments)
                    / ((1 + monthly_rate) ** installments - 1), 2)
    return {
        "financedAmount": financed,
        "disbursementAmount": amount,
        "paymentAmount": payment,
        "totalAmountOwed": round(payment * installments, 2),
        "monthlyEffectiveInterestRate": 1.99,
        "annualEffectiveInterestRate": 26.68,
        "iofAmount": round(amount * 0.03, 2),
        "disbursementDate": "2026-06-01",
    }
