# Agent Orchestration — Requirements

## Functional Requirements

### FR-AO-001: Supervisor Agent Creation
WHEN a user request arrives
THE SYSTEM SHALL create a Supervisor Agent configured with:
- BedrockModel from `supervisor.model_id_env` environment variable
- System prompt from `supervisor.prompt_file` (relative to domain dir)
- All sub-agents registered as `@tool` functions
- SlidingWindowConversationManager for context management
SO THAT the Supervisor can route user intent to the appropriate sub-agent.

### FR-AO-002: Agents-as-Tools Pattern
WHEN the domain config defines sub-agents
THE SYSTEM SHALL register each sub-agent as a `@tool(name="{key}_assistant")` function on the Supervisor
AND the tool's docstring SHALL be set from `tool_docstring` in domain.yaml
SO THAT the Supervisor LLM can read tool descriptions and decide which sub-agent to invoke.

### FR-AO-003: Dynamic Sub-Agent Creation
WHEN a delegate tool is invoked by the Supervisor
THE SYSTEM SHALL create a fresh sub-agent instance with:
- BedrockModel from the sub-agent's `model_id_env`
- System prompt from the sub-agent's `prompt_file`
- Tools resolved from `tools_source` (gateway_mcp, bedrock_kb, or none)
AND the sub-agent SHALL receive the query and return a text response.

### FR-AO-004: Tool Provider Registry
WHEN a sub-agent config specifies `tools_source`
THE SYSTEM SHALL resolve tools using the provider registry:
- `gateway_mcp` → MCP tools from AgentCore Gateway (Cognito OAuth)
- `bedrock_kb` → Bedrock KB `retrieve` tool
- `none` → empty tool list

### FR-AO-005: Degraded Mode
WHEN a tool provider fails (missing env var, connection error, import error)
THE SYSTEM SHALL log a warning and continue with an empty tool list
SO THAT the agent operates in degraded mode rather than crashing.

### FR-AO-006: Session Context Passing
WHEN a request is processed
THE SYSTEM SHALL store `user_id` and `session_id` in thread-local storage
AND delegate tool functions SHALL access this context to pass to sub-agents
SO THAT sub-agents can operate with the correct user context.

### FR-AO-007: Memory Session Manager (STM)
WHEN `AGENTCORE_MEMORY_ID` is configured and `user_id` is present
THE SYSTEM SHALL create an `AgentCoreMemorySessionManager` with:
- Memory namespaces from `domain.yaml` with template variables resolved
- Session ID from request or auto-generated as `{session_prefix}-{user_id}`
AND SHALL pass it in the Agent constructor for hooks to register.

### FR-AO-008: Long-Term Memory Tools (LTM)
WHEN `AGENTCORE_MEMORY_ID` is configured and `user_id` is present
THE SYSTEM SHALL attach LTM tools (read/write) to the Supervisor post-construction
SO THAT the agent can persist and retrieve user facts across sessions.

### FR-AO-009: Guardrails Integration
WHEN `BEDROCK_GUARDRAIL_ID` is configured
THE SYSTEM SHALL apply Bedrock Guardrails at the model level with:
- `guardrail_redact_input=False` (preserve conversation context)
- `guardrail_redact_output=False` (keep response readable)
- `guardrail_latest_message=True` (evaluate only last message)

### FR-AO-010: Cached Heavy Setup
WHEN multiple requests are processed
THE SYSTEM SHALL cache via `lru_cache`:
- BedrockModel instances (maxsize=4, one per model_id_env)
- System prompts (maxsize=8, read from disk once)
- Delegate tool functions (maxsize=1, created once from domain.yaml)
SO THAT only per-request setup (conversation manager, memory) is fresh.

### FR-AO-011: Response Text Extraction
WHEN a Strands Agent returns a result
THE SYSTEM SHALL extract text from `result.message.content[0].text`
AND SHALL fall back to `str(result)` if the format is unexpected.

## Non-Functional Requirements

### NFR-AO-001: Thread Safety
WHEN concurrent requests are processed
THE SYSTEM SHALL use thread-local storage for session context
AND SHALL create fresh Agent instances per request (Strands `_invocation_lock` prevents reuse).

### NFR-AO-002: New Agent Per Request
WHEN a request arrives
THE SYSTEM SHALL create a new Supervisor Agent instance
AND SHALL NOT reuse Agent instances across requests
BECAUSE Strands SDK uses `_invocation_lock` that prevents concurrent invocation (ADR-001).

### NFR-AO-003: Synchronous Execution
THE SYSTEM SHALL use synchronous execution throughout
AND SHALL NOT use async/await patterns
BECAUSE Strands SDK is synchronous (ADR-005).

### NFR-AO-004: Prompt Caching
WHEN system prompts are sent to Bedrock
THE SYSTEM SHALL include `cachePoint` markers for Bedrock prompt caching
SO THAT repeated prompts benefit from reduced latency.

## Acceptance Criteria

| ID | Criterion | Verified By |
|---|---|---|
| AC-AO-001 | SessionContext isolates state between threads | `test_context.py::test_thread_isolation` |
| AC-AO-002 | SessionContext snapshots are immutable | `test_context.py::test_immutable_snapshot` |
| AC-AO-003 | SessionContext set/get works correctly | `test_context.py::test_set_and_get` |
| AC-AO-004 | SessionContext defaults to None | `test_context.py::test_default_is_none` |
| AC-AO-005 | SessionContext clear resets state | `test_context.py::test_clear` |
| AC-AO-006 | Supervisor created with correct tools from domain.yaml | Integration test |
| AC-AO-007 | Sub-agent invoked via delegate tool returns text | Integration test |
| AC-AO-008 | Missing Gateway env var → degraded mode (no crash) | Integration test |
| AC-AO-009 | Missing Memory env var → agent works without memory | Integration test |
| AC-AO-010 | extract_text handles standard Strands response format | `test_agent_helpers.py` |
