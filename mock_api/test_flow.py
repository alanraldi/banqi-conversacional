"""
Testes do fluxo completo de contratação de empréstimo consignado.
Executa todos os cenários conforme a documentação (spec.md + po-brief.md).

Uso:
    python test_flow.py
"""
import time
import httpx

BASE = "http://localhost:8000"
PHONE = "+5511999990001"
CPF = "12345678901"
PARTNER = "banqi-test"

HEADERS = {
    "x-whatsapp-phone": PHONE,
    "x-document": CPF,
    "x-partner": PARTNER,
}

# ─── Utilitários ──────────────────────────────────────────────────────────────

def reset():
    httpx.delete(f"{BASE}/test/state/{PHONE}")

def wait_for_event(event_name: str, timeout: float = 5.0) -> dict | None:
    """Aguarda um evento específico chegar no log de webhooks."""
    deadline = time.time() + timeout
    while time.time() < deadline:
        r = httpx.get(f"{BASE}/test/webhooks/{PHONE}")
        events = r.json().get("events", [])
        for e in events:
            if e.get("event") == event_name:
                return e
        time.sleep(0.2)
    return None

def ok(label: str, condition: bool):
    status = "✅ PASS" if condition else "❌ FAIL"
    print(f"  {status}  {label}")
    return condition

def section(title: str):
    print(f"\n{'═'*55}")
    print(f"  {title}")
    print('═'*55)

# ─── Cenário 1: Fluxo Feliz — Etapas 1 a 7 ───────────────────────────────────

def test_happy_path():
    section("CENÁRIO 1 — Fluxo completo (happy path)")
    reset()
    passed = []

    # ── Etapa 1 — Termo de Consentimento ─────────────────────────────────────
    print("\n[ETAPA 1] Gerando Termo de Consentimento...")
    r = httpx.post(f"{BASE}/v1/whatsapp/consent-term",
                   headers=HEADERS, json={"name": "João da Silva"})
    passed.append(ok("POST /consent-term → 202", r.status_code == 202))

    event = wait_for_event("CONSENT_TERM_FILE_READY")
    passed.append(ok("Webhook CONSENT_TERM_FILE_READY recebido", event is not None))
    if event:
        passed.append(ok("PDF em base64 presente", bool(event["consentTerm"]["pdf"])))
        passed.append(ok("Status do termo = CREATED", event["consentTerm"]["status"] == "CREATED"))

    # ── Etapa 2 — Aceite + Simulação Automática ───────────────────────────────
    print("\n[ETAPA 2] Aceitando termo e aguardando simulação automática...")
    r = httpx.post(f"{BASE}/v1/whatsapp/consent-term/accept",
                   headers=HEADERS,
                   json={"ip": "189.100.50.25", "userAgent": "WhatsApp/2.23.0"})
    passed.append(ok("POST /consent-term/accept → 200", r.status_code == 200))

    event = wait_for_event("SIMULATION_READY")
    passed.append(ok("Webhook SIMULATION_READY recebido", event is not None))
    if event:
        sim = event["simulation"]["simulations"][0]
        passed.append(ok("Simulação com amount > 0", sim["amount"] > 0))
        passed.append(ok("SimulationData presente", "simulationData" in sim))
        id_simulation_auto = sim["idSimulation"]
        print(f"    → Valor disponível: R$ {sim['amount']:,.2f} em {sim['numInstallments']}x "
              f"de R$ {sim['simulationData']['paymentAmount']:,.2f}")

    # ── Etapa 3 — Simulação Manual (valor diferente) ──────────────────────────
    print("\n[ETAPA 3] Simulando valor personalizado: R$ 5.000 em 12x...")
    r = httpx.post(f"{BASE}/v1/whatsapp/simulations",
                   headers=HEADERS,
                   json={"amount": 5000.0, "numInstallments": [12]})
    passed.append(ok("POST /simulations → 202 (cache miss)", r.status_code == 202))
    id_correlation = r.json()["idCorrelation"]

    event = wait_for_event("SIMULATION_COMPLETED")
    passed.append(ok("Webhook SIMULATION_COMPLETED recebido", event is not None))
    if event:
        sim = event["simulation"]["simulations"][0]
        id_simulation = sim["idSimulation"]
        passed.append(ok("Status = SUCCESS", event["simulation"]["status"] == "SUCCESS"))
        passed.append(ok("Amount = 5000", sim["amount"] == 5000.0))
        passed.append(ok("Installments = 12", sim["numInstallments"] == 12))
        print(f"    → R$ {sim['amount']:,.2f} em {sim['numInstallments']}x "
              f"de R$ {sim['simulationData']['paymentAmount']:,.2f} "
              f"| CET {sim['simulationData']['monthlyEffectiveInterestRate']}% a.m.")

    # Cache hit (mesmos parâmetros)
    r = httpx.post(f"{BASE}/v1/whatsapp/simulations",
                   headers=HEADERS,
                   json={"amount": 5000.0, "numInstallments": [12]})
    passed.append(ok("POST /simulations → 200 (cache hit)", r.status_code == 200))

    # GET fallback
    r = httpx.get(f"{BASE}/v1/whatsapp/simulations", headers=HEADERS)
    passed.append(ok("GET /simulations → 200", r.status_code == 200))

    # ── Etapa 4 — Dados Cadastrais + Proposta ────────────────────────────────
    print("\n[ETAPA 4] Criando proposta com dados cadastrais...")
    payload = {
        "idSimulation": id_simulation,
        "email": "joao.silva@email.com",
        "address": {
            "street": "Rua das Flores",
            "number": "789",
            "complement": "Apto 42",
            "neighborhood": "Centro",
            "city": "Rio de Janeiro",
            "state": "RJ",
            "country": "Brasil",
            "zipCode": "20040030",
        },
        "bankAccount": {
            "bankCode": "341",
            "bankBranch": "1234",
            "bankAccount": "12345",
            "bankAccountDigit": "6",
            "bankAccountType": "CHECKING",
        },
    }
    r = httpx.post(f"{BASE}/v1/whatsapp/proposals", headers=HEADERS, json=payload)
    passed.append(ok("POST /proposals → 202", r.status_code == 202))
    id_proposal = r.json()["idProposal"]

    event = wait_for_event("PROPOSAL_CREATED")
    passed.append(ok("Webhook PROPOSAL_CREATED recebido", event is not None))
    if event:
        passed.append(ok("idProposal presente", bool(event["proposal"]["idProposal"])))
        print(f"    → idProposal: {id_proposal}")

    # ── Etapa 5 — Biometria ───────────────────────────────────────────────────
    print("\n[ETAPA 5] Biometria (liveness + face match)...")
    r = httpx.post(f"{BASE}/v1/whatsapp/proposals/{id_proposal}/biometry",
                   headers=HEADERS, json={})
    passed.append(ok("POST /biometry → 201", r.status_code == 201))
    id_anti_fraud = r.json()["idAntiFraud"]
    passed.append(ok("idAntiFraud retornado", bool(id_anti_fraud)))
    passed.append(ok("Status = BIOMETRICS", r.json()["status"] == "BIOMETRICS"))
    print(f"    → BioLink gerado para idAntiFraud: {id_anti_fraud[:8]}...")

    id_biometric = "bio-approved-" + id_anti_fraud[:8]
    r = httpx.post(f"{BASE}/v1/whatsapp/proposals/{id_proposal}/biometry/continue",
                   headers=HEADERS,
                   json={"idAntiFraud": id_anti_fraud,
                         "idBiometric": id_biometric,
                         "provider": "unico"})
    passed.append(ok("POST /biometry/continue → 200", r.status_code == 200))
    passed.append(ok("Status = APPROVED", r.json()["status"] == "APPROVED"))
    print("    → Biometria APROVADA ✅")

    # ── Etapa 6 — Aceite Formal ───────────────────────────────────────────────
    print("\n[ETAPA 6] Registrando aceite formal do contrato...")
    accept_headers = {**HEADERS,
                      "x-remote-address": "189.100.50.25",
                      "user-agent": "WhatsApp/2.23.0 iOS/16.0"}
    r = httpx.post(f"{BASE}/v1/whatsapp/proposals/{id_proposal}/accept",
                   headers=accept_headers,
                   json={"idBiometric": id_biometric})
    passed.append(ok("POST /accept → 200", r.status_code == 200))

    # ── Etapa 7 — Acompanhamento de Status ───────────────────────────────────
    print("\n[ETAPA 7] Aguardando ciclo completo de status...")
    expected_statuses = ["ACCEPTED", "SIGNED", "CCB_GENERATED",
                         "FORMALIZED", "PENDING_DISBURSEMENT", "DISBURSED"]

    time.sleep(8)  # Aguarda todos os webhooks do ciclo (último delay = 2.5s + margem)

    events = httpx.get(f"{BASE}/test/webhooks/{PHONE}").json()["events"]
    status_events = [e for e in events if e.get("event") == "PROPOSAL_STATUS_UPDATE"]
    received_statuses = [e["proposal"]["newStatus"] for e in status_events]

    for st in expected_statuses:
        passed.append(ok(f"Status {st} recebido", st in received_statuses))

    print(f"    → Ciclo: {' → '.join(received_statuses)}")

    # ── Resultado ─────────────────────────────────────────────────────────────
    total = len(passed)
    ok_count = sum(passed)
    print(f"\n  Resultado: {ok_count}/{total} checks passaram")
    return ok_count == total


# ─── Cenário 2: Sem Elegibilidade ─────────────────────────────────────────────

def test_eligibility_rejected():
    section("CENÁRIO 2 — Cliente sem elegibilidade (ELIGIBILITY_REJECTED)")

    phone = "+5511999990002"
    cpf = "00012345678"  # CPF iniciando com "000" → rejeitado
    headers = {"x-whatsapp-phone": phone, "x-document": cpf, "x-partner": PARTNER}
    httpx.delete(f"{BASE}/test/state/{phone}")

    passed = []

    r = httpx.post(f"{BASE}/v1/whatsapp/consent-term",
                   headers=headers, json={"name": "Maria Sem Margem"})
    passed.append(ok("POST /consent-term → 202", r.status_code == 202))

    time.sleep(1.5)
    r = httpx.post(f"{BASE}/v1/whatsapp/consent-term/accept",
                   headers=headers, json={"ip": "10.0.0.1"})
    passed.append(ok("POST /consent-term/accept → 200", r.status_code == 200))

    time.sleep(1.5)
    events = httpx.get(f"{BASE}/test/webhooks/{phone}").json()["events"]
    no_offer = next((e for e in events if e.get("event") == "NO_OFFER_AVAILABLE"), None)
    passed.append(ok("Webhook NO_OFFER_AVAILABLE recebido", no_offer is not None))
    if no_offer:
        passed.append(ok("errorCode = ELIGIBILITY_REJECTED",
                         no_offer["errorCode"] == "ELIGIBILITY_REJECTED"))
        print(f"    → {no_offer['errorCode']}: {no_offer.get('reason', '')}")

    total = len(passed)
    ok_count = sum(passed)
    print(f"\n  Resultado: {ok_count}/{total} checks passaram")
    return ok_count == total


# ─── Cenário 3: Biometria Reprovada ───────────────────────────────────────────

def test_biometry_denied():
    section("CENÁRIO 3 — Biometria reprovada (DENIED)")

    phone = "+5511999990003"
    cpf = "11122233344"
    headers = {"x-whatsapp-phone": phone, "x-document": cpf, "x-partner": PARTNER}
    httpx.delete(f"{BASE}/test/state/{phone}")
    passed = []

    # Etapas 1-4 rápidas
    httpx.post(f"{BASE}/v1/whatsapp/consent-term", headers=headers, json={"name": "Pedro Bio"})
    time.sleep(1.2)
    httpx.post(f"{BASE}/v1/whatsapp/consent-term/accept", headers=headers, json={"ip": "10.0.0.2"})
    time.sleep(1.2)

    events = httpx.get(f"{BASE}/test/webhooks/{phone}").json()["events"]
    sim_event = next((e for e in events if e.get("event") == "SIMULATION_READY"), None)
    id_simulation = sim_event["simulation"]["simulations"][0]["idSimulation"]

    r = httpx.post(f"{BASE}/v1/whatsapp/proposals", headers=headers, json={
        "idSimulation": id_simulation,
        "email": "pedro@test.com",
        "address": {"street": "Rua A", "number": "1", "neighborhood": "B",
                    "city": "SP", "state": "SP", "country": "Brasil", "zipCode": "01310100"},
        "bankAccount": {"bankCode": "001", "bankBranch": "0001", "bankAccount": "12345",
                        "bankAccountDigit": "6", "bankAccountType": "CHECKING"},
    })
    time.sleep(1.2)

    id_proposal = r.json()["idProposal"]

    r = httpx.post(f"{BASE}/v1/whatsapp/proposals/{id_proposal}/biometry", headers=headers, json={})
    id_anti_fraud = r.json()["idAntiFraud"]
    passed.append(ok("Biometria iniciada", r.status_code == 201))

    # idBiometric começando com "denied" → reprovado
    r = httpx.post(f"{BASE}/v1/whatsapp/proposals/{id_proposal}/biometry/continue",
                   headers=headers,
                   json={"idAntiFraud": id_anti_fraud,
                         "idBiometric": "denied-fake-bio-id",
                         "provider": "unico"})
    passed.append(ok("POST /biometry/continue → 200", r.status_code == 200))
    passed.append(ok("Status = DENIED", r.json()["status"] == "DENIED"))
    print(f"    → Biometria REPROVADA ❌ — fluxo encerrado")

    total = len(passed)
    ok_count = sum(passed)
    print(f"\n  Resultado: {ok_count}/{total} checks passaram")
    return ok_count == total


# ─── Cenário 4: Erros Síncronos ───────────────────────────────────────────────

def test_sync_errors():
    section("CENÁRIO 4 — Erros síncronos (409, 412, 422)")

    phone = "+5511999990004"
    cpf = "55566677788"
    headers = {"x-whatsapp-phone": phone, "x-document": cpf, "x-partner": PARTNER}
    httpx.delete(f"{BASE}/test/state/{phone}")
    passed = []

    # Criar termo
    httpx.post(f"{BASE}/v1/whatsapp/consent-term", headers=headers, json={"name": "Erro Test"})
    time.sleep(1.2)

    # 409 — Aceitar termo já ativo (TOKEN_GENERATED)
    httpx.post(f"{BASE}/v1/whatsapp/consent-term/accept", headers=headers, json={"ip": "10.0.0.3"})
    time.sleep(1.2)
    r = httpx.post(f"{BASE}/v1/whatsapp/consent-term/accept", headers=headers, json={"ip": "10.0.0.3"})
    passed.append(ok("409 ao aceitar termo já aceito", r.status_code == 409))

    # 412 — Criar proposta sem simulação
    r = httpx.post(f"{BASE}/v1/whatsapp/proposals", headers=headers, json={
        "idSimulation": "inexistente-uuid-0000",
        "email": "x@x.com",
        "address": {"street": "R", "number": "1", "neighborhood": "B",
                    "city": "SP", "state": "SP", "country": "Brasil", "zipCode": "01000000"},
        "bankAccount": {"bankCode": "001", "bankBranch": "0001", "bankAccount": "111",
                        "bankAccountDigit": "1", "bankAccountType": "CHECKING"},
    })
    passed.append(ok("412 ao criar proposta com simulação inválida", r.status_code == 412))

    # 409 — Recriar termo para usuário com termo ativo
    r = httpx.post(f"{BASE}/v1/whatsapp/consent-term", headers=headers, json={"name": "Erro Test"})
    passed.append(ok("409 ao criar segundo termo com TOKEN_GENERATED ativo", r.status_code == 409))

    total = len(passed)
    ok_count = sum(passed)
    print(f"\n  Resultado: {ok_count}/{total} checks passaram")
    return ok_count == total


# ─── Runner ───────────────────────────────────────────────────────────────────

if __name__ == "__main__":
    print("\n" + "█"*55)
    print("  banQi Mock API — Testes de Fluxo Conversacional")
    print("█"*55)

    # Verificar se servidor está no ar
    try:
        httpx.get(f"{BASE}/docs", timeout=2)
    except Exception:
        print("\n❌ Servidor não encontrado em localhost:8000")
        print("   Execute primeiro: uvicorn mock_api.server:app --reload")
        exit(1)

    results = []
    results.append(("Fluxo Completo (happy path)", test_happy_path()))
    results.append(("Elegibilidade Rejeitada", test_eligibility_rejected()))
    results.append(("Biometria Reprovada", test_biometry_denied()))
    results.append(("Erros Síncronos", test_sync_errors()))

    section("RESULTADO FINAL")
    total_pass = sum(1 for _, r in results if r)
    for name, result in results:
        print(f"  {'✅' if result else '❌'}  {name}")
    print(f"\n  {total_pass}/{len(results)} cenários passaram\n")
