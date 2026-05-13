"""Funções de validação para o domínio consignado banQi."""

from __future__ import annotations

import re

MAX_INPUT_LENGTH = 4096
VALID_ACCOUNT_TYPES = {"CHECKING", "SAVINGS", "PAYMENT", "SALARY"}
VALID_INSTALLMENTS = {12, 24, 36, 48, 60}
MIN_LOAN_AMOUNT = 500.0
MAX_LOAN_AMOUNT = 50_000.0


def validate_cpf(cpf: str) -> bool:
    """Valida CPF brasileiro (11 dígitos + dígitos verificadores)."""
    digits = re.sub(r"\D", "", cpf)
    if len(digits) != 11:
        return False
    if digits == digits[0] * 11:
        return False
    for i in (9, 10):
        total = sum(int(digits[j]) * ((i + 1) - j) for j in range(i))
        expected = (total * 10 % 11) % 10
        if int(digits[i]) != expected:
            return False
    return True


def validate_email(email: str) -> bool:
    """Valida formato básico de email."""
    pattern = re.compile(r"^[A-Za-z0-9._%+-]+@[A-Za-z0-9.-]+\.[A-Za-z]{2,}$")
    return bool(pattern.match(email.strip()))


def validate_cep(cep: str) -> bool:
    """Valida CEP brasileiro (8 dígitos numéricos)."""
    digits = re.sub(r"\D", "", cep)
    return len(digits) == 8


def validate_bank_code(code: str) -> bool:
    """Valida código de banco (3 dígitos numéricos, 001-999)."""
    digits = re.sub(r"\D", "", code.strip())
    return len(digits) == 3 and digits.isdigit()


def validate_account_type(account_type: str) -> bool:
    """Valida tipo de conta aceito pela API banQi."""
    return account_type.strip().upper() in VALID_ACCOUNT_TYPES


def validate_name(name: str) -> bool:
    """Valida nome completo (mínimo 2 palavras, apenas letras e espaços)."""
    name = name.strip()
    if not re.match(r"^[A-Za-zÀ-ÿ\s]+$", name):
        return False
    words = [w for w in name.split() if len(w) >= 2]
    return len(words) >= 2


def validate_loan_amount(amount: float) -> bool:
    """Valida valor do empréstimo (entre R$ 500 e R$ 50.000)."""
    return MIN_LOAN_AMOUNT <= amount <= MAX_LOAN_AMOUNT


def validate_installments(installments: int) -> bool:
    """Valida número de parcelas (12, 24, 36, 48 ou 60)."""
    return installments in VALID_INSTALLMENTS


def format_cpf_masked(cpf_digits: str) -> str:
    """Formata CPF para exibição — mostra apenas últimos 3 dígitos."""
    if len(cpf_digits) != 11:
        return "***.***.***-**"
    return f"***.***.*{cpf_digits[8:10]}-{cpf_digits[10:]}"


def normalize_account_type(raw: str) -> str | None:
    """Normaliza tipo de conta do input do usuário para o formato da API."""
    mapping = {
        "corrente": "CHECKING", "checking": "CHECKING",
        "poupanca": "SAVINGS", "poupança": "SAVINGS", "savings": "SAVINGS",
        "pagamento": "PAYMENT", "payment": "PAYMENT",
        "salario": "SALARY", "salário": "SALARY", "salary": "SALARY",
    }
    normalized = raw.strip().lower()
    return mapping.get(normalized) or (raw.strip().upper() if validate_account_type(raw) else None)
