# API & Payloads Reference

## AgentCore Runtime — Invoke Endpoint

The agent is deployed as an AgentCore Runtime container. The `@app.entrypoint` receives a JSON payload and returns a JSON response.

### Request Payload

```json
{
  "prompt": "Qual é meu saldo?",
  "phone_number": "5511999998888",
  "session_id": "session-5511999998888"
}
```

| Field | Type | Required | Description |
|---|---|---|---|
| `prompt` | string | Yes | User message text |
| `phone_number` | string | No | WhatsApp phone number (used as user_id) |
| `user_id` | string | No | Alternative user identifier |
| `session_id` | string | No | Session ID (auto-generated as `{session_prefix}-{user_id}` if absent) |

**Prompt extraction order**: `payload.prompt` → `payload.input.prompt`

**User ID extraction order**: `phone_number` → `from` → `wa_id` → `user_id` → `"anonymous"`

User IDs are sanitized: only `[a-zA-Z0-9\-_+]` kept, max 64 chars.

### Response

```json
{
  "result": "Seu saldo atual é R$ 1.234,56. Deseja ver as últimas transações?"
}
```

| Field | Type | Description |
|---|---|---|
| `result` | string | Agent response text |

On error, returns `error_messages.generic` from `domain.yaml`.
On empty input, returns `error_messages.empty_input`.

### Health Check

```
GET /ping → "Healthy"
```

---

## WhatsApp Webhook — Lambda

The WhatsApp channel uses a Lambda function behind API Gateway + WAF.

### Webhook Verification (GET)

Meta sends a GET request to verify the webhook URL.

```
GET /webhook?hub.mode=subscribe&hub.verify_token=<token>&hub.challenge=<challenge>
```

Returns the `hub.challenge` value if `hub.verify_token` matches.

### Incoming Message (POST)

Meta sends a POST with HMAC-SHA256 signature in `X-Hub-Signature-256` header.

```json
{
  "object": "whatsapp_business_account",
  "entry": [{
    "id": "BUSINESS_ACCOUNT_ID",
    "changes": [{
      "value": {
        "messaging_product": "whatsapp",
        "metadata": {
          "display_phone_number": "551140028922",
          "phone_number_id": "PHONE_NUMBER_ID"
        },
        "contacts": [{
          "profile": { "name": "José" },
          "wa_id": "5511999998888"
        }],
        "messages": [{
          "id": "wamid.UNIQUE_ID",
          "from": "5511999998888",
          "timestamp": "1714300000",
          "type": "text",
          "text": { "body": "Qual meu saldo?" }
        }]
      },
      "field": "messages"
    }]
  }]
}
```

### Lambda Response

```json
{
  "statusCode": 200,
  "body": "OK"
}
```

The Lambda processes asynchronously — it sends the response to WhatsApp via the WhatsApp Business API (POST to `graph.facebook.com`), not in the webhook response.

### Message Deduplication

DynamoDB table stores `message_id` with TTL (24h). Duplicate webhook deliveries are silently dropped.

### Supported Message Types

| Type | Status |
|---|---|
| `text` | ✅ Supported |
| `image` | ⏳ Planned |
| `audio` | ⏳ Planned |
| `video` | ⏳ Planned |
| `document` | ⏳ Planned |

Only `text` messages are processed in v1. Other types are parsed but ignored.

---

## Chainlit — Dev/Test Interface

Local development interface at `http://localhost:8000`.

### Start

```bash
chainlit run src/channels/chainlit/app.py
```

Uses the same `create_supervisor()` factory as AgentCore Runtime. No separate API — Chainlit handles the UI and message routing internally.
