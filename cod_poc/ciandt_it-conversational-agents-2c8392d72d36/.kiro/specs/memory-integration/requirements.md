# Memory Integration — Requirements

## Functional Requirements

### FR-MI-001: STM Session Manager
WHEN a user request arrives with a user_id
THE SYSTEM SHALL create an `AgentCoreMemorySessionManager` with namespaces from `domain.yaml`
AND SHALL pass it in the Agent constructor for hooks to register.

### FR-MI-002: Namespace Template Resolution
WHEN building retrieval config
THE SYSTEM SHALL resolve `{user_id}` and `{session_id}` placeholders in namespace paths
WITH `top_k` and `relevance_score` from each namespace config.

### FR-MI-003: LTM Tools
WHEN memory is configured
THE SYSTEM SHALL attach `AgentCoreMemoryToolProvider` tools (read/write) to the Supervisor
SO THAT the agent can persist and retrieve user facts across sessions.

### FR-MI-004: Conversation Persistence
WHEN the WhatsApp Lambda receives a successful agent response
THE SYSTEM SHALL persist the USER+ASSISTANT turn via `create_event`
SO THAT LTM strategies (SEMANTIC, USER_PREFERENCE, SUMMARIZATION) can process the data.

### FR-MI-005: Degraded Mode
WHEN `AGENTCORE_MEMORY_ID` is not configured
THE SYSTEM SHALL log a warning and continue without memory.

## Non-Functional Requirements

### NFR-MI-001: PII in Logs
THE SYSTEM SHALL mask user_id in memory-related logs (show only last 4 chars).

## Acceptance Criteria

| ID | Criterion | Verified By |
|---|---|---|
| AC-MI-001 | Memory attached when AGENTCORE_MEMORY_ID set | Integration test |
| AC-MI-002 | Agent works without memory when ID not set | Integration test |
| AC-MI-003 | Namespace templates resolved correctly | Integration test |
| AC-MI-004 | create_event persists USER+ASSISTANT turns | E2E test |
