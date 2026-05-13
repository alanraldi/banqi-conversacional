# Channel Chainlit — Tasks

## Status: ✅ Complete (Fase 3)

---

## T-CL-001: Channel Adapter Base
- [x] Create `src/channels/base.py`
- [x] `IncomingMessage` and `OutgoingResponse` frozen dataclasses
- [x] `ChannelAdapter` ABC with `receive_message()`, `send_response()`, optional `verify_webhook()`, `send_typing_indicator()`

**Files:** `src/channels/base.py`

## T-CL-002: Chainlit App
- [x] Create `src/channels/chainlit/app.py`
- [x] Load domain config at module level (fail-fast)
- [x] `on_chat_start` — session UUID + welcome message
- [x] `on_message` — create_supervisor → invoke → extract_text → respond
- [x] Error handling with `error_messages.generic`
- [x] Channel toggle check (exit if disabled)

**Files:** `src/channels/chainlit/app.py`

---

## Reconstruction Guide

1. **Build base.py** — Abstract `ChannelAdapter` with normalized message types. This is the extension point for future channels (Telegram, Slack).

2. **Build app.py** — Thin Chainlit adapter. Load config, check channel enabled, wire `on_chat_start`/`on_message` to `create_supervisor()`.

**Key principle:** Chainlit is a thin wrapper — all intelligence is in the agent factory. If Chainlit works, production works.
