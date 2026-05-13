# Channel Chainlit — Requirements

## Functional Requirements

### FR-CL-001: Welcome Message
WHEN a user opens the Chainlit interface
THE SYSTEM SHALL display the `interface.welcome_message` from `domain.yaml`.

### FR-CL-002: Message Routing
WHEN a user sends a message
THE SYSTEM SHALL create a Supervisor Agent via `create_supervisor()` and invoke it with the message text
AND SHALL display the response with `interface.author_name`.

### FR-CL-003: Session Management
WHEN a chat session starts
THE SYSTEM SHALL generate a unique session ID (`chainlit-{uuid}`) and user ID
AND SHALL pass them to `create_supervisor()` for memory context.

### FR-CL-004: Channel Toggle
WHEN the `chainlit` channel is disabled in `domain.yaml`
THE SYSTEM SHALL exit immediately with an error message.

### FR-CL-005: Error Handling
WHEN the agent raises an exception
THE SYSTEM SHALL display `error_messages.generic` from `domain.yaml` instead of crashing.

## Non-Functional Requirements

### NFR-CL-001: Dev Only
THE SYSTEM SHALL include `chainlit` as a dev dependency only (`[project.optional-dependencies.dev]`)
AND SHALL NOT be deployed to production.

### NFR-CL-002: Same Pipeline
THE SYSTEM SHALL use the exact same `create_supervisor()` factory as production channels
SO THAT local testing reflects production behavior.

## Acceptance Criteria

| ID | Criterion | Verified By |
|---|---|---|
| AC-CL-001 | Welcome message displayed from domain.yaml | Manual test |
| AC-CL-002 | Messages routed through Supervisor Agent | Manual test |
| AC-CL-003 | Error returns generic message, not stack trace | Manual test |
| AC-CL-004 | Channel adapter base is extensible | `tests/unit/channels/test_channel_extensibility.py` |
