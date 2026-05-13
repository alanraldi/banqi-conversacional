#!/usr/bin/env bash
# Test: AgentCore /invocations endpoint
set -euo pipefail

echo "=== Invocation Test ==="
response=$(curl -sf -X POST http://localhost:8080/invocations \
    -H "Content-Type: application/json" \
    -d '{"prompt": "Olá", "user_id": "test-user"}')

if echo "$response" | grep -q '"result"'; then
    echo "PASS: /invocations returned result"
    echo "Response: $response"
else
    echo "FAIL: unexpected response"
    echo "Response: $response"
    exit 1
fi
