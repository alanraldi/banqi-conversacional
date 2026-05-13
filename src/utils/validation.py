"""Funções de validação para o domínio consignado banQi.

Sem dependências externas — apenas stdlib Python.
"""

from __future__ import annotations

import re

MAX_INPUT_LENGTH = 4096

# Tipos de conta aceitos pela API banQi
VALID_ACCOUNT_TYPES = {"CHECKING", "SAVINGS", "PAYMENT", "SALARY"}

# Parcelas aceitas para empréstimo consignado
VALID_INSTALLMENTS = {12, 24, 36, 48, 60}

# Faixa de valor do empréstimo (em reais)
MIN_LOAN_AMOUNT = 500.0
MAX_LOAN_AMOUNT = 50_000.0


def validate_cpf(cpf: str) -> bool:
    """Valida CPF brasileiro (11 dígitos + dígitos verificadores).

    Rejeita sequências repetidas (ex: 111.111.111-11).

    Args:
        cpf: CPF em qualquer formato (com ou sem pontuação).

    Returns:
        True se válido, False caso contrário.
    """
    digits = re.sub(r"\D", "", cpf)

    if len(digits) != 11:
        return False

    # Sequências repetidas são inválidas
    if digits == digits[0] * 11:
        return False

    # Valida os dois dígitos verificadores
    for i in (9, 10):
        total = sum(int(digits[j]) * ((i + 1) - j) for j in range(i))
        expected = (total * 10 % 11) % 10
        if int(digits[i]) != expected:
            return False

    return True


def validate_email(email: str) -> bool:
    """Valida formato básico de email.

    Args:
        email: Endereço de email a validar.

    Returns:
        True se o formato for válido.
    """
    pattern = re.compile(r"^[A-Za-z0-9._%+-]+@[A-Za-z0-9.-]+\.[A-Za-z]{2,}$")
    return bool(pattern.match(email.strip()))


def validate_cep(cep: str) -> bool:
    """Valida CEP brasileiro (8 dígitos numéricos).

    Args:
        cep: CEP com ou sem hífen (ex: 01310-100 ou 01310100).

    Returns:
        True se tiver exatamente 8 dígitos numéricos.
    """
    digits = re.sub(r"\D", "", cep)
    return len(digits) == 8


def validate_bank_code(code: str) -> bool:
    """Valida código de banco (3 dígitos numéricos, 001-999).

    Args:
        code: Código do banco (ex: "001", "341").

    Returns:
        True se for 3 dígitos numéricos.
    """
    digits = re.sub(r"\D", "", code.strip())
    return len(digits) == 3 and digits.isdigit()


def validate_account_type(account_type: str) -> bool:
    """Valida tipo de conta aceito pela API banQi.

    Valores aceitos: CHECKING, SAVINGS, PAYMENT, SALARY

    Args:
        account_type: Tipo de conta (case-insensitive).

    Returns:
        True se for um tipo válido.
    """
    return account_type.strip().upper() in VALID_ACCOUNT_TYPES


def validate_name(name: str) -> bool:
    """Valida nome completo (mínimo 2 palavras, apenas letras e espaços).

    Args:
        name: Nome completo do cliente.

    Returns:
        True se tiver pelo menos 2 palavras compostas apenas por letras.
    """
    name = name.strip()
    # Permite letras com acentos, cedilha e espaços
    if not re.match(r"^[A-Za-zÀ-ÿ\s]+$", name):
        return False
    words = [w for w in name.split() if len(w) >= 2]
    return len(words) >= 2


def validate_non_empty(value: str | None, field_name: str) -> str:
    """Rejeita strings vazias ou apenas whitespace.

    Args:
        value: Valor a validar.
        field_name: Nome do campo (para mensagem de erro).

    Returns:
        Valor limpo (stripped).

    Raises:
        ValueError: Se valor for vazio ou None.
    """
    if not value or not value.strip():
        raise ValueError(f"{field_name} não pode ser vazio.")
    return value.strip()


def validate_input_length(value: str, max_length: int = MAX_INPUT_LENGTH) -> str:
    """Rejeita input muito longo (previne abuso LLM — OWASP LLM04).

    Args:
        value: Texto do input.
        max_length: Tamanho máximo permitido.

    Returns:
        Valor original se dentro do limite.

    Raises:
        ValueError: Se exceder o limite.
    """
    if len(value) > max_length:
        raise ValueError(f"Input excede o limite de {max_length} caracteres.")
    return value


def validate_loan_amount(amount: float) -> bool:
    """Valida valor do empréstimo (entre R$ 500 e R$ 50.000).

    Args:
        amount: Valor em reais.

    Returns:
        True se dentro do range permitido.
    """
    return MIN_LOAN_AMOUNT <= amount <= MAX_LOAN_AMOUNT


def validate_installments(installments: int) -> bool:
    """Valida número de parcelas (12, 24, 36, 48 ou 60).

    Args:
        installments: Número de parcelas desejado.

    Returns:
        True se for um valor permitido.
    """
    return installments in VALID_INSTALLMENTS


def format_cpf_masked(cpf_digits: str) -> str:
    """Formata CPF para exibição — mostra apenas últimos 3 dígitos.

    Seguro para exibir em respostas do chat (complementa o Guardrail).

    Args:
        cpf_digits: CPF normalizado (11 dígitos sem pontuação).

    Returns:
        CPF mascarado: ***.***.*XX-YY
    """
    if len(cpf_digits) != 11:
        return "***.***.***-**"
    return f"***.***.*{cpf_digits[8:10]}-{cpf_digits[10:]}"


def normalize_account_type(raw: str) -> str | None:
    """Normaliza tipo de conta do input do usuário para o formato da API.

    Args:
        raw: Input do usuário (ex: "corrente", "poupança", "Corrente").

    Returns:
        Tipo normalizado (CHECKING, SAVINGS, PAYMENT, SALARY) ou None se inválido.
    """
    mapping = {
        "corrente": "CHECKING",
        "checking": "CHECKING",
        "poupanca": "SAVINGS",
        "poupança": "SAVINGS",
        "savings": "SAVINGS",
        "pagamento": "PAYMENT",
        "payment": "PAYMENT",
        "salario": "SALARY",
        "salário": "SALARY",
        "salary": "SALARY",
    }
    normalized = raw.strip().lower()
    return mapping.get(normalized) or (raw.strip().upper() if validate_account_type(raw) else None)
