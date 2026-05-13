"""CloudFormation template validation — zero AWS cost.

Validates structure, IAM least-privilege (C4), and naming conventions.
"""

from __future__ import annotations

from pathlib import Path

import pytest
import yaml

_TEMPLATE_PATH = Path(__file__).resolve().parents[3] / "infrastructure" / "cloudformation" / "template.yaml"


def _cfn_yaml_load(text: str) -> dict:
    """Load CloudFormation YAML handling intrinsic function tags (!Ref, !GetAtt, etc.)."""

    class CfnLoader(yaml.SafeLoader):
        pass

    cfn_tags = (
        "Ref",
        "GetAtt",
        "Sub",
        "Join",
        "Select",
        "Split",
        "If",
        "Equals",
        "And",
        "Or",
        "Not",
        "FindInMap",
        "Base64",
        "Cidr",
        "GetAZs",
        "ImportValue",
        "Condition",
    )
    for tag in cfn_tags:
        CfnLoader.add_constructor(f"!{tag}", lambda loader, node: loader.construct_scalar(node))
        CfnLoader.add_multi_constructor(f"!{tag}", lambda loader, suffix, node: loader.construct_scalar(node))

    return yaml.load(text, Loader=CfnLoader)


@pytest.fixture()
def template() -> dict:
    return _cfn_yaml_load(_TEMPLATE_PATH.read_text())


class TestCloudFormationTemplate:
    """US-15/US-24: CloudFormation template validation."""

    def test_template_is_valid_yaml(self):
        assert _TEMPLATE_PATH.exists()
        _cfn_yaml_load(_TEMPLATE_PATH.read_text())

    def test_has_required_parameters(self, template):
        params = template.get("Parameters", {})
        for required in ("DomainSlug", "AgentName", "Environment"):
            assert required in params, f"Missing parameter: {required}"

    def test_has_outputs(self, template):
        outputs = template.get("Outputs", {})
        assert len(outputs) > 0

    @pytest.mark.critical
    def test_iam_no_wildcard_resource(self, template):
        """C4: No IAM policy uses Resource: '*'."""
        resources = template.get("Resources", {})
        for logical_id, resource in resources.items():
            if resource.get("Type") not in ("AWS::IAM::Policy", "AWS::IAM::Role"):
                continue
            props = resource.get("Properties", {})
            _assert_no_wildcard_in_props(logical_id, props)

    def test_no_hardcoded_domain_names(self, template):
        """US-15 AC3: No hardcoded domain-specific names."""
        text = yaml.dump(template).lower()
        for term in ("banqi", "banking", "paf"):
            assert term not in text, f"Hardcoded domain term found: {term}"

    def test_dynamodb_has_ttl(self, template):
        resources = template.get("Resources", {})
        for lid, res in resources.items():
            if res.get("Type") == "AWS::DynamoDB::Table":
                ttl = res.get("Properties", {}).get("TimeToLiveSpecification", {})
                assert ttl.get("Enabled") is True, f"{lid} missing TTL"


def _assert_no_wildcard_in_props(logical_id: str, props: dict) -> None:
    """Recursively check for Resource: '*' in IAM policy documents."""
    for key, val in props.items():
        if key == "PolicyDocument" and isinstance(val, dict):
            for stmt in val.get("Statement", []):
                res = stmt.get("Resource", "")
                if isinstance(res, str):
                    assert res != "*", f"{logical_id} has Resource: '*'"
                elif isinstance(res, list):
                    assert "*" not in res, f"{logical_id} has Resource: '*' in list"
        elif isinstance(val, dict):
            _assert_no_wildcard_in_props(logical_id, val)
