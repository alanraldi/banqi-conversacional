"""Unit tests for src/utils/pii.py — zero AWS dependencies."""

from __future__ import annotations

import logging

from src.utils.pii import PIIMaskingFilter, mask_pii


class TestMaskPII:
    def test_masks_cpf_formatted(self):
        assert "***.***.***-**" in mask_pii("CPF: 529.982.247-25")

    def test_masks_email(self):
        assert "***@***.***" in mask_pii("Email: user@example.com")

    def test_masks_phone_unformatted(self):
        assert "5511999887766" not in mask_pii("Phone: 5511999887766")

    def test_no_pii_unchanged(self):
        assert mask_pii("Hello world") == "Hello world"

    def test_masks_multiple_pii(self):
        result = mask_pii("CPF 529.982.247-25 email user@test.com")
        assert "529" not in result
        assert "user@test" not in result


class TestPIIMaskingFilter:
    def test_filter_masks_message(self):
        f = PIIMaskingFilter()
        record = logging.LogRecord(
            name="test",
            level=logging.INFO,
            pathname="",
            lineno=0,
            msg="User CPF: 529.982.247-25",
            args=None,
            exc_info=None,
        )
        f.filter(record)
        assert "529.982" not in record.msg

    def test_filter_masks_tuple_args(self):
        f = PIIMaskingFilter()
        record = logging.LogRecord(
            name="test",
            level=logging.INFO,
            pathname="",
            lineno=0,
            msg="Data: %s",
            args=("user@example.com",),
            exc_info=None,
        )
        f.filter(record)
        assert "***@***.***" in record.args[0]

    def test_filter_masks_dict_args(self):
        f = PIIMaskingFilter()
        record = logging.LogRecord(
            name="test",
            level=logging.INFO,
            pathname="",
            lineno=0,
            msg="%(email)s",
            args=None,
            exc_info=None,
        )
        record.args = {"email": "user@example.com"}
        f.filter(record)
        assert "***@***.***" in record.args["email"]

    def test_filter_always_returns_true(self):
        f = PIIMaskingFilter()
        record = logging.LogRecord(
            name="test",
            level=logging.INFO,
            pathname="",
            lineno=0,
            msg="safe",
            args=None,
            exc_info=None,
        )
        assert f.filter(record) is True
