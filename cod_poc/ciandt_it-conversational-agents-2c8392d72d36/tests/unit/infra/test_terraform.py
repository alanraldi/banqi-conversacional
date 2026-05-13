"""Terraform module validation — zero AWS cost.

Checks file structure, no wildcard resources, and naming.
terraform validate requires `terraform` CLI (skipped if not installed).
"""

from __future__ import annotations

import re
import subprocess
from pathlib import Path

import pytest

_TF_DIR = Path(__file__).resolve().parents[3] / "infrastructure" / "terraform"


class TestTerraformModules:
    """US-15/US-26: Terraform validation."""

    def test_root_module_files_exist(self):
        for f in ("main.tf", "variables.tf", "outputs.tf", "providers.tf"):
            assert (_TF_DIR / f).exists(), f"Missing {f}"

    def test_sub_modules_exist(self):
        for mod in ("iam", "runtime", "memory", "gateway"):
            assert (_TF_DIR / "modules" / mod / "main.tf").exists(), f"Missing module {mod}"

    @pytest.mark.critical
    def test_no_wildcard_resource_in_iam(self):
        """C4: No resources = ['*'] in any .tf file."""
        for tf_file in _TF_DIR.rglob("*.tf"):
            content = tf_file.read_text()
            # Match: resources = ["*"] or resources = [ "*" ]
            assert not re.search(
                r'resources\s*=\s*\[\s*"\*"\s*\]', content
            ), f'{tf_file.name} contains resources = ["*"]'

    def test_no_hardcoded_domain_names(self):
        for tf_file in _TF_DIR.rglob("*.tf"):
            content = tf_file.read_text().lower()
            for term in ("banqi", "banking", "paf"):
                assert term not in content, f"{tf_file.name} has hardcoded: {term}"

    def test_variables_have_descriptions(self):
        content = (_TF_DIR / "variables.tf").read_text()
        var_blocks = re.findall(r'variable\s+"(\w+)"', content)
        assert len(var_blocks) >= 4
        assert "description" in content

    def test_terraform_validate(self):
        """Runs terraform validate (skipped if CLI not available)."""
        try:
            subprocess.run(["terraform", "version"], capture_output=True, check=True)
        except (FileNotFoundError, subprocess.CalledProcessError):
            pytest.skip("terraform CLI not installed")

        result = subprocess.run(
            ["terraform", "init", "-backend=false"],
            cwd=_TF_DIR,
            capture_output=True,
            text=True,
        )
        assert result.returncode == 0, f"init failed: {result.stderr}"

        result = subprocess.run(
            ["terraform", "validate"],
            cwd=_TF_DIR,
            capture_output=True,
            text=True,
        )
        assert result.returncode == 0, f"validate failed: {result.stderr}"
