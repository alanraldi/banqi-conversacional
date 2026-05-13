"""CDK stack validation — zero AWS cost.

Validates Python syntax, IAM patterns, and naming conventions.
CDK synth requires `cdk` CLI + deps (skipped if not available).
"""

from __future__ import annotations

import ast
from pathlib import Path

import pytest

_CDK_DIR = Path(__file__).resolve().parents[3] / "infrastructure" / "cdk"


class TestCDKStacks:
    """US-15/US-25: CDK Python validation."""

    def test_stack_files_exist(self):
        for f in ("app.py", "cdk.json", "requirements.txt"):
            assert (_CDK_DIR / f).exists(), f"Missing {f}"
        assert (_CDK_DIR / "stacks" / "agentcore_stack.py").exists()

    def test_python_syntax_valid(self):
        for py_file in _CDK_DIR.rglob("*.py"):
            ast.parse(py_file.read_text())

    @pytest.mark.critical
    def test_no_wildcard_resource_in_iam(self):
        """C4: No iam.PolicyStatement(resources=['*'])."""
        for py_file in _CDK_DIR.rglob("*.py"):
            content = py_file.read_text()
            assert 'resources=["*"]' not in content, f'{py_file.name} has resources=["*"]'
            assert "resources=['*']" not in content, f"{py_file.name} has resources=['*']"

    def test_has_cdk_nag(self):
        app_content = (_CDK_DIR / "app.py").read_text()
        assert "cdk_nag" in app_content, "app.py missing cdk-nag"

    def test_has_cfn_outputs(self):
        stack = (_CDK_DIR / "stacks" / "agentcore_stack.py").read_text()
        assert "CfnOutput" in stack, "Missing CfnOutput in agentcore_stack"

    def test_no_hardcoded_domain_names(self):
        for py_file in _CDK_DIR.rglob("*.py"):
            content = py_file.read_text().lower()
            for term in ("banqi", "paf-conversational"):
                assert term not in content, f"{py_file.name} has hardcoded: {term}"
