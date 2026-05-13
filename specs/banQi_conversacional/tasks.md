# Tasks — MVP Empréstimo Consignado via WhatsApp

## Status
- [ ] = pendente
- [~] = em andamento
- [x] = concluído

---

## Fase 0 — Setup e Infraestrutura

- [ ] **T-01** Criar conta AWS e configurar landing zone (VPC, subnets, VPC Endpoints)
- [ ] **T-02** Configurar ECR e fazer build/push do container Docker ARM64 base (da PoC)
- [ ] **T-03** Provisionar AgentCore Runtime via Terraform (módulo `runtime`)
- [ ] **T-04** Provisionar AgentCore Memory via Terraform (módulo `memory`)
- [ ] **T-05** Provisionar AgentCore Gateway via Terraform (módulo `gateway`) — configurar endpoints das APIs banQi
- [ ] **T-06** Provisionar Lambda + API Gateway + DynamoDB para webhook WhatsApp (módulo `whatsapp`)
- [ ] **T-07** Configurar Bedrock Guardrails com regras de escopo (só consignado) e proteção PII
- [ ] **T-08** Configurar Secrets Manager com credenciais do WhatsApp Business e banQi
- [ ] **T-09** Conectar número WhatsApp Business ao webhook (Meta Developer Console)

**Critério de aceite:** Lambda recebe e processa webhook de teste do WhatsApp sem erro.

---

## Fase 1 — Estrutura dos Agentes

- [ ] **T-10** Criar `domain.yaml` do domínio `banqi-consignado` com config de agentes, memória e namespaces LTM
- [ ] **T-11** Implementar **Supervisor Agent** com:
  - Routing: consignado_agent vs general_agent
  - Memória-aware: recupera LTM antes de delegar
  - Enriquecimento de contexto na delegação (padrão da PoC)
- [ ] **T-12** Implementar **Consignado Agent** com estrutura base (sem tools ainda):
  - Sistema de etapas (`current_step`)
  - Coleta progressiva (um campo por mensagem)
  - Validações dos campos (CPF, e-mail, CEP, banco, conta)
  - Mascaramento de PII nas mensagens
- [ ] **T-13** Implementar **General Agent** com mensagem padrão de escopo
- [ ] **T-14** Escrever prompt do Supervisor (`prompts/supervisor.md`)
- [ ] **T-15** Escrever prompt do Consignado Agent (`prompts/consignado.md`)
- [ ] **T-16** Configurar memória: namespaces LTM `users/{phone}/consignado`

**Critério de aceite:** Conversa básica funciona via Chainlit local sem chamar APIs.

---

## Fase 2 — Tools / Integração com APIs banQi

Cada task = uma tool + integração via AgentCore Gateway.

- [ ] **T-17** Tool `create_consent_term` — `POST /v1/whatsapp/consent-term` (Etapa 1)
  - Tratar erros síncronos: 406, 409
  - Aguardar webhook `CONSENT_TERM_FILE_READY`

- [ ] **T-18** Tool `accept_consent_term` — `POST /v1/whatsapp/consent-term/accept` (Etapa 2)
  - Capturar IP e user-agent automaticamente
  - Aguardar webhook `SIMULATION_READY` ou `NO_OFFER_AVAILABLE`

- [ ] **T-19** Tool `create_simulation` — `POST /v1/whatsapp/simulations` (Etapa 3)
  - Tratar cache hit (200) e cache miss (202)
  - Tratar erro `TOKEN_EXPIRED` (422)

- [ ] **T-20** Tool `get_simulations` — `GET /v1/whatsapp/simulations` (Etapa 3 fallback)
  - Usar como fallback se webhook `SIMULATION_COMPLETED` for perdido

- [ ] **T-21** Tool `create_proposal` — `POST /v1/whatsapp/proposals` (Etapa 4)
  - Montar payload completo com endereço e dados bancários
  - Aguardar webhook `PROPOSAL_CREATED`

- [ ] **T-22** Tool `start_biometry` — `POST /v1/whatsapp/proposals/{id}/biometry` (Etapa 5)
  - Gerar e enviar BioLink ao cliente via WhatsApp

- [ ] **T-23** Tool `continue_biometry` — `POST /v1/whatsapp/proposals/{id}/biometry/continue` (Etapa 5)
  - Tratar status: APPROVED, BIOMETRICS, DENIED

- [ ] **T-24** Tool `accept_proposal` — `POST /v1/whatsapp/proposals/{id}/accept` (Etapa 6)
  - Capturar IP e user-agent do device do cliente

**Critério de aceite:** Cada tool chamada individualmente retorna resposta esperada contra sandbox banQi.

---

## Fase 3 — Webhook Handler

- [ ] **T-25** Implementar roteamento de webhooks por evento no Lambda handler:
  - `CONSENT_TERM_FILE_READY` → enviar PDF + solicitar aceite
  - `NO_OFFER_AVAILABLE` → tratar por `errorCode`
  - `SIMULATION_READY` → apresentar simulação automática
  - `SIMULATION_COMPLETED` → apresentar simulação manual
  - `PROPOSAL_CREATED` → salvar `idProposal` na LTM + iniciar Etapa 5
  - `PROPOSAL_STATUS_UPDATE` → enviar mensagem de status ao cliente

- [ ] **T-26** Implementar correlação de webhooks com sessão ativa (via `phone` e `idCorrelation`)
- [ ] **T-27** Implementar tratamento de webhooks com sessão expirada (cliente offline)
- [ ] **T-28** Implementar retry para webhooks não processados (DLQ)

**Critério de aceite:** Todos os 6 eventos processados corretamente em testes de integração.

---

## Fase 4 — Fluxo End-to-End

- [ ] **T-29** Testar fluxo completo (Etapas 1–7) no Chainlit local com sandbox banQi
- [ ] **T-30** Testar retomada de conversa (cliente abandona na Etapa 3 e volta depois)
- [ ] **T-31** Testar todos os caminhos de erro:
  - `ELIGIBILITY_REJECTED`
  - `TOKEN_EXPIRED`
  - Biometria `DENIED`
  - `ERROR` na proposta
- [ ] **T-32** Testar deduplicação (enviar mesma mensagem duas vezes rapidamente)
- [ ] **T-33** Testar via WhatsApp real contra sandbox banQi

**Critério de aceite:** Fluxo completo funciona do "oi" até o `DISBURSED` sem intervenção humana.

---

## Fase 5 — Qualidade e Produção

- [ ] **T-34** Escrever testes unitários: validações, mascaramento PII, roteamento
- [ ] **T-35** Escrever testes de integração: cada tool contra sandbox
- [ ] **T-36** Escrever testes E2E: fluxo completo em staging
- [ ] **T-37** Configurar CI/CD (pipeline de build + deploy automático)
- [ ] **T-38** Configurar dashboards CloudWatch (latência, erros, conversas ativas)
- [ ] **T-39** Testes de carga (simular 1.000 conversas simultâneas)
- [ ] **T-40** Testes de segurança: prompt injection, jailbreak, PII leak
- [ ] **T-41** Documentação final + handover para o time banQi

**Critério de aceite:** Passar todos os testes. Latência P95 < 5s. Zero PII em logs.

---

## Dependências entre fases

```
Fase 0 (infra) → Fase 1 (agentes) → Fase 2 (tools) → Fase 3 (webhooks)
                                                              ↓
                                                       Fase 4 (E2E)
                                                              ↓
                                                       Fase 5 (qualidade)
```

Fase 1 pode rodar em paralelo com Fase 0 usando Chainlit local.
Fases 2 e 3 podem ser desenvolvidas em paralelo após Fase 1 estar estável.

---

## Estimativa de esforço

| Fase | Tasks | Estimativa |
|---|---|---|
| 0 — Setup infra | T-01 a T-09 | 1 semana |
| 1 — Agentes | T-10 a T-16 | 1 semana |
| 2 — Tools/APIs | T-17 a T-24 | 2 semanas |
| 3 — Webhooks | T-25 a T-28 | 1 semana |
| 4 — E2E | T-29 a T-33 | 1 semana |
| 5 — Qualidade | T-34 a T-41 | 2 semanas |
| **Total** | **41 tasks** | **~8 semanas** |
