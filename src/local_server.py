"""Servidor local para testar o webhook handler sem Lambda/AWS.

Expõe dois endpoints:
  POST /whatsapp   — simula mensagem recebida do WhatsApp
  POST /webhook    — simula webhook banQi recebido do backend
  GET  /ping       — health check

Uso:
  python -m src.local_server
  # ou via docker-compose
"""

from __future__ import annotations

import json
import os

import uvicorn
from fastapi import FastAPI, Request, Response

from src.utils.logging import configure_logging
from src.webhook.handler import lambda_handler

configure_logging()

app = FastAPI(title="banQi Conversacional — Local Dev Server")


@app.get("/ping")
def ping() -> dict:
    return {"status": "ok", "env": os.environ.get("APP_ENV", "dev")}


@app.post("/whatsapp")
async def whatsapp_webhook(request: Request) -> Response:
    """Simula uma mensagem WhatsApp recebida."""
    body = await request.body()
    headers = dict(request.headers)

    event = {
        "httpMethod": "POST",
        "path": "/whatsapp",
        "headers": headers,
        "body": body.decode("utf-8"),
    }

    result = lambda_handler(event, None)
    return Response(
        content=result.get("body", ""),
        status_code=result.get("statusCode", 200),
        media_type="application/json",
    )


@app.post("/webhook/banqi")
async def banqi_webhook(request: Request) -> Response:
    """Simula um webhook banQi recebido do backend."""
    body = await request.body()
    headers = dict(request.headers)

    event = {
        "httpMethod": "POST",
        "path": "/webhook/banqi",
        "headers": headers,
        "body": body.decode("utf-8"),
    }

    result = lambda_handler(event, None)
    return Response(
        content=result.get("body", ""),
        status_code=result.get("statusCode", 200),
        media_type="application/json",
    )


@app.get("/webhook/verify")
async def whatsapp_verify(request: Request) -> Response:
    """Simula a verificação do webhook WhatsApp (GET hub.challenge)."""
    params = dict(request.query_params)
    event = {
        "httpMethod": "GET",
        "path": "/whatsapp",
        "queryStringParameters": params,
    }
    result = lambda_handler(event, None)
    return Response(
        content=result.get("body", ""),
        status_code=result.get("statusCode", 200),
    )


if __name__ == "__main__":
    uvicorn.run("src.local_server:app", host="0.0.0.0", port=8080, reload=True)
