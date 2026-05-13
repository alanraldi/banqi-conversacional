"""Input validation framework — reusable validators per domain."""

from __future__ import annotations

import re

from pydantic import BaseModel, field_validator

MAX_INPUT_LENGTH = 4096


class CPFInput(BaseModel):
    """Validates and normalizes Brazilian CPF (11 digits with check digits)."""

    value: str

    @field_validator("value")
    @classmethod
    def validate_cpf(cls, v: str) -> str:
        digits = re.sub(r"\D", "", v)
        if len(digits) != 11:
            raise ValueError("CPF deve ter 11 dígitos. Exemplo: 123.456.789-00")
        if digits == digits[0] * 11:
            raise ValueError("CPF inválido.")
        for i in (9, 10):
            total = sum(int(digits[j]) * ((i + 1) - j) for j in range(i))
            digit = (total * 10 % 11) % 10
            if int(digits[i]) != digit:
                raise ValueError("CPF inválido.")
        return digits


class PhoneInput(BaseModel):
    """Validates and normalizes phone number (10-15 digits)."""

    value: str

    @field_validator("value")
    @classmethod
    def validate_phone(cls, v: str) -> str:
        digits = re.sub(r"\D", "", v)
        if not 10 <= len(digits) <= 15:
            raise ValueError("Telefone deve ter entre 10 e 15 dígitos.")
        return digits


def validate_non_empty(value: str | None, field_name: str) -> str:
    """Reject empty/whitespace strings with user-friendly message."""
    if not value or not value.strip():
        raise ValueError(f"{field_name} não pode ser vazio.")
    return value.strip()


def validate_input_length(value: str, max_length: int = MAX_INPUT_LENGTH) -> str:
    """Reject oversized input to prevent LLM abuse (OWASP LLM04)."""
    if len(value) > max_length:
        raise ValueError(f"Input excede o limite de {max_length} caracteres.")
    return value


def format_cpf_masked(cpf_digits: str) -> str:
    """Format CPF for user-facing messages — market standard (***.***.*89-00).

    Shows only last 4 digits. Safe for display in chat responses
    built by code (not by LLM — those are handled by Guardrails).

    Args:
        cpf_digits: Normalized CPF (11 digits, no punctuation).

    Returns:
        Masked CPF string.
    """
    if len(cpf_digits) != 11:
        return "***.***.***-**"
    return f"***.***.*{cpf_digits[8:10]}-{cpf_digits[10:]}"
