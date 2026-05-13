# Fluxo Conversacional — Empréstimo Consignado via WhatsApp

## Legenda
- **[A]** = Agente fala
- **[C]** = Cliente fala
- **[API]** = Chamada à API banQi
- **[WH]** = Webhook recebido do backend
- **[MEM]** = Salvar na memória LTM

---

## Etapa 1 — Saudação e Termo de Consentimento

```
[C] "Oi" / "Quero um empréstimo" / qualquer mensagem

[A] "Olá! Sou o assistente do banQi para empréstimo consignado.
    Para começar, qual é o seu CPF? (somente números)"

[C] "12345678900"

[A] "Obrigado! E qual é o seu nome completo?"

[C] "João da Silva"

[MEM] cpf = "12345678900", name = "João da Silva", current_step = 1

[API] POST /v1/whatsapp/consent-term
      body: { name: "João da Silva" }
      → 202 (aguardando)

[A] "Estou gerando seu Termo de Consentimento. Um momento..."

[WH] CONSENT_TERM_FILE_READY
     → consentTerm.pdf (base64)

[A] [envia o PDF]
    "Aqui está o Termo de Consentimento.
    Por favor, leia com atenção.
    Para prosseguir, responda ACEITO."

[C] "ACEITO" / "aceito" / "sim"
```

**Erros possíveis na Etapa 1:**
```
→ 406 (3+ CPFs no telefone):
[A] "Este número já possui o limite de CPFs vinculados.
    Entre em contato com o suporte banQi."

→ 409 (já tem termo ativo):
    Pular direto para verificar etapa atual na memória.

→ NO_OFFER_AVAILABLE (PDF_GENERATION_ERROR):
[A] "Tivemos um problema técnico. Pode tentar novamente?"
```

---

## Etapa 2 — Aceite e Simulação Automática

```
[API] POST /v1/whatsapp/consent-term/accept
      body: { ip: "189.100.50.25", userAgent: "WhatsApp/2.23.0" }
      → 200 (aguardando)

[A] "Processando sua solicitação e verificando sua elegibilidade..."

[WH] SIMULATION_READY
     → simulations[0]: valor, parcelas, CET, data de depósito

[MEM] current_step = 3

[A] "Boa notícia! Encontramos uma oferta para você:

    💰 Valor disponível: R$ 8.000,00
    📅 Parcelas: 24x de R$ 490,50
    📊 Taxa mensal (CET): 1,99%
    📆 Depósito previsto: 01/05/2026

    Deseja prosseguir com esses valores ou prefere simular outro valor?"
```

**Erros possíveis na Etapa 2:**
```
→ NO_OFFER_AVAILABLE (ELIGIBILITY_REJECTED):
[A] "Infelizmente não encontramos uma oferta disponível para você neste momento.
    Se quiser, pode tentar novamente em alguns dias."
    [encerrar fluxo]

→ NO_OFFER_AVAILABLE (TOKEN_GENERATION_ERROR):
[A] "Não conseguimos verificar seus dados agora. Tente novamente em instantes."

→ NO_OFFER_AVAILABLE (SIMULATION_ERROR):
[A] "Tivemos um problema ao simular. Pode tentar novamente?"
```

---

## Etapa 3 — Simulação (caminho A: aceita automática)

```
[C] "Quero prosseguir" / "pode ser" / "sim"

[MEM] id_simulation = "uuid-da-simulacao-auto"
      simulation_amount = 8000, simulation_installments = 24
      current_step = 4

→ Avançar direto para Etapa 4
```

## Etapa 3 — Simulação (caminho B: quer ajustar)

```
[C] "Quero simular R$ 5.000 em 12 vezes"

[API] POST /v1/whatsapp/simulations
      body: { amount: 5000.00, numInstallments: [12] }

  → 200 (cache hit):
    [A] "Aqui está a simulação com os valores que você escolheu:
        💰 Valor: R$ 5.000,00
        📅 Parcelas: 12x de R$ 520,50
        📊 Taxa mensal (CET): 1,99%
        📆 Depósito previsto: 01/05/2026
        Deseja prosseguir?"

  → 202 (cache miss):
    [A] "Calculando a simulação com esses valores..."
    [WH] SIMULATION_COMPLETED
    → mesma apresentação acima

[C] "Sim, quero prosseguir"

[MEM] id_simulation = "uuid-da-sim-manual"
      simulation_amount = 5000, simulation_installments = 12
      current_step = 4
```

**Erros possíveis na Etapa 3:**
```
→ 422 TOKEN_EXPIRED:
[A] "Seu acesso expirou. Preciso gerar um novo termo de consentimento.
    Pode confirmar seu CPF novamente?"
    [reiniciar da Etapa 1]
```

---

## Etapa 4 — Dados Cadastrais e Proposta

```
[A] "Ótimo! Agora preciso de alguns dados para criar sua proposta.
    Qual é o seu e-mail?"

[C] "joao.silva@email.com"
[MEM] email = "joao.silva@email.com"

[A] "Qual é o seu CEP?"

[C] "20040030"

[A] "Encontrei o endereço: Rua das Flores, Centro, Rio de Janeiro - RJ.
    Qual é o número?"

[C] "789"

[A] "Tem complemento? (Apto, Sala etc. — ou responda 'não')"

[C] "Apto 42"
[MEM] address = { street, number, complement, neighborhood, city, state, zipCode }

[A] "Agora preciso dos dados da conta para depositar o valor.
    Qual é o código ou nome do seu banco?"

[C] "Itaú" / "341"

[A] "Qual é o número da agência?"
[C] "1234"

[A] "Qual é o número da conta com o dígito? (ex: 12345-6)"
[C] "12345-6"

[A] "Tipo de conta:
    1. Corrente
    2. Poupança
    3. Pagamento
    4. Salário"

[C] "1" / "Corrente"
[MEM] bank_account = { bankCode, bankBranch, bankAccount, bankAccountDigit, bankAccountType }

[A] "Vou confirmar os dados antes de criar sua proposta:

    📧 E-mail: j***@email.com
    📍 Endereço: Rua das Flores, 789 - Apto 42, Centro, Rio de Janeiro/RJ
    🏦 Banco Itaú | Ag. 1234 | Conta Corrente

    Está tudo correto? Responda SIM para confirmar."

[C] "SIM"

[API] POST /v1/whatsapp/proposals
      body: { idSimulation, email, address, bankAccount }
      → 202

[A] "Criando sua proposta..."

[WH] PROPOSAL_CREATED
     → idProposal = "uuid-proposta"

[MEM] id_proposal = "uuid-proposta", current_step = 5
```

---

## Etapa 5 — Biometria

```
[A] "Proposta criada! Agora precisamos confirmar sua identidade.
    Vou enviar um link para você fazer uma selfie rápida.
    É seguro e leva menos de 1 minuto. Preparado?"

[C] "Sim"

[API] POST /v1/whatsapp/proposals/{idProposal}/biometry
      → idAntiFraud + BioLink

[A] "Acesse o link abaixo e siga as instruções para a verificação facial:
    🔗 [BioLink]

    Assim que concluir, me avise aqui."

[C] "Pronto" / "Feito" / "Ok"
    (SDK Único retorna idBiometric via callback)

[API] POST /v1/whatsapp/proposals/{idProposal}/biometry/continue
      body: { idAntiFraud, idBiometric, provider: "unico" }

  → status: APPROVED:
    [MEM] current_step = 6
    → avançar para Etapa 6

  → status: BIOMETRICS (ainda processando):
    [A] "Ainda verificando... pode levar mais alguns segundos."
    (tentar novamente)

  → status: DENIED:
    [A] "Não conseguimos confirmar sua identidade.
        Por segurança, não podemos prosseguir com a contratação.
        Entre em contato com o suporte banQi se precisar de ajuda."
    [encerrar fluxo]
```

---

## Etapa 6 — Aceite Formal

```
[A] "Identidade confirmada! ✅

    Antes de finalizar, confirme que concorda com a contratação:
    💰 Empréstimo de R$ 5.000,00
    📅 12 parcelas de R$ 520,50

    Responda CONFIRMAR para assinar o contrato."

[C] "CONFIRMAR"

[API] POST /v1/whatsapp/proposals/{idProposal}/accept
      body: { idBiometric }
      headers: { x-remote-address, user-agent }
      → 200

[A] "Contrato enviado para assinatura! Vou te avisando sobre o andamento."

[MEM] current_step = 7
```

---

## Etapa 7 — Acompanhamento de Status

```
[WH] PROPOSAL_STATUS_UPDATE → newStatus: ACCEPTED
[A] "Proposta recebida! Estamos processando seu contrato. 🔄"

[WH] PROPOSAL_STATUS_UPDATE → newStatus: SIGNED
[A] "Ótima notícia! Seu contrato foi assinado digitalmente. ✍️"

[WH] PROPOSAL_STATUS_UPDATE → newStatus: CCB_GENERATED
[A] "Cédula de Crédito Bancária registrada com sucesso. 📄"

[WH] PROPOSAL_STATUS_UPDATE → newStatus: FORMALIZED
[A] "Averbação aprovada! Aguardando o desembolso. ⏳"

[WH] PROPOSAL_STATUS_UPDATE → newStatus: PENDING_DISBURSEMENT
[A] "Desembolso agendado para 01/05/2026. Quase lá! 📅"

[WH] PROPOSAL_STATUS_UPDATE → newStatus: DISBURSED
[A] "🎉 R$ 5.000,00 depositado na sua conta!
    Bom proveito, João! Qualquer dúvida, estou por aqui."

[MEM] flow_status = "completed"
```

**Erros na Etapa 7:**
```
[WH] PROPOSAL_STATUS_UPDATE → newStatus: CANCELED
[A] "Sua proposta foi cancelada.
    Posso ajudar a entender o motivo ou iniciar uma nova simulação?"

[WH] PROPOSAL_STATUS_UPDATE → newStatus: ERROR
[A] "Ocorreu um problema no processamento da sua proposta.
    Entre em contato com o suporte banQi para mais informações."
```

---

## Resumo do Fluxo

```
CLIENTE                    AGENTE                      API / WEBHOOK
  │                          │                              │
  │ "Oi"                     │                              │
  │─────────────────────────►│                              │
  │                          │ Solicita CPF e nome          │
  │◄─────────────────────────│                              │
  │ CPF + Nome               │                              │
  │─────────────────────────►│                              │
  │                          │ POST /consent-term ─────────►│
  │                          │◄────────── CONSENT_TERM_FILE_READY
  │ Recebe PDF               │                              │
  │◄─────────────────────────│                              │
  │ "ACEITO"                 │                              │
  │─────────────────────────►│                              │
  │                          │ POST /consent-term/accept ──►│
  │                          │◄──────────── SIMULATION_READY
  │ Recebe simulação         │                              │
  │◄─────────────────────────│                              │
  │ Escolhe valores          │                              │
  │─────────────────────────►│                              │
  │                          │ POST /simulations ──────────►│
  │                          │◄───────── SIMULATION_COMPLETED
  │ Confirma simulação       │                              │
  │─────────────────────────►│                              │
  │                          │ (coleta e-mail, end., banco) │
  │◄────────────────────────►│                              │
  │                          │ POST /proposals ────────────►│
  │                          │◄──────────── PROPOSAL_CREATED
  │                          │ POST /biometry ─────────────►│
  │ Recebe BioLink           │                              │
  │◄─────────────────────────│                              │
  │ (faz biometria)          │                              │
  │ "Pronto"                 │                              │
  │─────────────────────────►│                              │
  │                          │ POST /biometry/continue ────►│
  │                          │◄────── { status: APPROVED }  │
  │ Confirma contrato        │                              │
  │─────────────────────────►│                              │
  │                          │ POST /accept ───────────────►│
  │                          │◄──── PROPOSAL_STATUS_UPDATE  │
  │ Updates de status        │      (ACCEPTED → DISBURSED)  │
  │◄─────────────────────────│                              │
```

---

## Cenários de Retomada de Conversa

O agente retoma o fluxo do ponto onde parou usando `current_step` da memória LTM.

| `current_step` | Comportamento ao retornar |
|---|---|
| 0 | Iniciar do zero |
| 1 | "Ainda estou gerando seu termo. Um momento..." |
| 2 | "Processando seu aceite. Aguarde..." |
| 3 | Reapresentar simulação disponível e perguntar se quer prosseguir |
| 4 | Continuar coletando dados de onde parou |
| 5 | "Ainda precisamos concluir a biometria. Posso reenviar o link?" |
| 6 | "Ainda precisa confirmar o contrato. Deseja prosseguir?" |
| 7 | Verificar status atual e informar o cliente |
