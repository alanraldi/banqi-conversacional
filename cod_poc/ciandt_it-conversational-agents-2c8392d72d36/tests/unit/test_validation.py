"""Unit tests for src/utils/validation.py — zero AWS dependencies."""

from __future__ import annotations

import pytest
from pydantic import ValidationError

from src.utils.validation import (
    CPFInput,
    PhoneInput,
    format_cpf_masked,
    validate_input_length,
    validate_non_empty,
)


class TestCPFInput:
    """C5: CPF validation with check digits."""

    def test_valid_cpf_digits_only(self):
        result = CPFInput(value="52998224725")
        assert result.value == "52998224725"

    def test_valid_cpf_formatted(self):
        result = CPFInput(value="529.982.247-25")
        assert result.value == "52998224725"

    def test_invalid_cpf_wrong_length(self):
        with pytest.raises(ValidationError, match="11 dígitos"):
            CPFInput(value="1234567")

    def test_invalid_cpf_all_same_digits(self):
        with pytest.raises(ValidationError, match="inválido"):
            CPFInput(value="11111111111")

    def test_invalid_cpf_wrong_check_digit(self):
        with pytest.raises(ValidationError, match="inválido"):
            CPFInput(value="52998224726")


class TestPhoneInput:
    """C5: Phone validation."""

    def test_valid_phone_11_digits(self):
        result = PhoneInput(value="11999887766")
        assert result.value == "11999887766"

    def test_valid_phone_with_country_code(self):
        result = PhoneInput(value="+55 11 99988-7766")
        assert result.value == "5511999887766"

    def test_invalid_phone_too_short(self):
        with pytest.raises(ValidationError, match="10 e 15"):
            PhoneInput(value="12345")

    def test_invalid_phone_too_long(self):
        with pytest.raises(ValidationError, match="10 e 15"):
            PhoneInput(value="1234567890123456")


class TestValidateNonEmpty:
    def test_valid_string(self):
        assert validate_non_empty("hello", "field") == "hello"

    def test_strips_whitespace(self):
        assert validate_non_empty("  hello  ", "field") == "hello"

    def test_empty_string_raises(self):
        with pytest.raises(ValueError, match="vazio"):
            validate_non_empty("", "prompt")

    def test_none_raises(self):
        with pytest.raises(ValueError, match="vazio"):
            validate_non_empty(None, "prompt")

    def test_whitespace_only_raises(self):
        with pytest.raises(ValueError, match="vazio"):
            validate_non_empty("   ", "prompt")


class TestValidateInputLength:
    def test_within_limit(self):
        assert validate_input_length("short") == "short"

    def test_exceeds_limit(self):
        with pytest.raises(ValueError, match="limite"):
            validate_input_length("x" * 5000)

    def test_custom_limit(self):
        with pytest.raises(ValueError, match="limite"):
            validate_input_length("hello", max_length=3)


class TestFormatCPFMasked:
    def test_masks_cpf(self):
        assert format_cpf_masked("52998224725") == "***.***.*72-5"

    def test_invalid_length_returns_full_mask(self):
        assert format_cpf_masked("123") == "***.***.***-**"
