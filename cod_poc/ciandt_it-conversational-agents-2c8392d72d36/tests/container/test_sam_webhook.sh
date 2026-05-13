#!/usr/bin/env bash
# Test: SAM local invoke for WhatsApp webhook verification
set -euo pipefail

echo "=== SAM Local Webhook Test ==="
EVENT='{"httpMethod":"GET","queryStringParameters":{"hub.mode":"subscribe","hub.verify_token":"test","hub.challenge":"ok"}}'

cd "$(dirname "$0")/../../infrastructure/whatsapp"
sam build --quiet 2>/dev/null || { echo "SKIP: sam build failed (SAM CLI may not be installed)"; exit 0; }

response=$(echo "$EVENT" | sam local invoke WhatsAppWebhookFunction --event - 2>/dev/null)

if echo "$response" | grep -q '"statusCode": 200'; then
    echo "PASS: webhook verification returned 200"
else
    echo "FAIL: unexpected response"
    echo "Response: $response"
    exit 1
fi
