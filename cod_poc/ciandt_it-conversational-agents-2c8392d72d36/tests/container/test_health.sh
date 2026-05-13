#!/usr/bin/env bash
# Test: AgentCore container health check
set -euo pipefail

echo "=== Container Health Check ==="
response=$(curl -sf -o /dev/null -w "%{http_code}" http://localhost:8080/ping)
if [ "$response" = "200" ]; then
    echo "PASS: /ping returned 200"
else
    echo "FAIL: /ping returned $response"
    exit 1
fi
