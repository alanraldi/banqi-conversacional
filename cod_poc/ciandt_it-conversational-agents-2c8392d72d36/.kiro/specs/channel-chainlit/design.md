# Channel Chainlit — Design

## Overview

Chainlit is the **dev/test interface** for local development. It provides a web UI at `http://localhost:8000` that routes messages through the same `create_supervisor()` pipeline as production (WhatsApp/AgentCore Runtime). Not for production — Chainlit is a dev dependency.

## Architecture

```
Browser (localhost:8000)
    │
    ▼
Chainlit (app.py)
    ├── on_chat_start → welcome_message from domain.yaml
    └── on_message → create_supervisor() → extract_text() → respond
```

## Component Design

### Chainlit App (`src/channels/chainlit/app.py`)

- Loads `DomainConfig` at module level (fail-fast)
- Checks if `chainlit` channel is enabled in `domain.yaml`
- `on_chat_start`: generates session UUID, displays `interface.welcome_message`
- `on_message`: creates Supervisor, invokes with message text, responds with `interface.author_name`
- Error handling: catches all exceptions, returns `error_messages.generic`

### Channel Adapter Base (`src/channels/base.py`)

Abstract base class for all channels (ISP — Interface Segregation):
- `IncomingMessage` — normalized message (text, user_id, channel, raw_metadata)
- `OutgoingResponse` — response (text, user_id)
- `ChannelAdapter` — abstract with `receive_message()`, `send_response()`, optional `verify_webhook()`, `send_typing_indicator()`

## Dependencies

- `chainlit` (dev dependency only)
- `src/agents/factory` — `create_supervisor()`
- `src/domain/loader` — domain config
- `src/utils/agent_helpers` — `extract_text()`

## Usage

```bash
chainlit run src/channels/chainlit/app.py
# → http://localhost:8000
```
