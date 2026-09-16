import pytest

from automation.capability.schema import Action, ActionType, RiskLevel, Target
from automation.safety.guardrails import Guardrails, GuardrailViolation, redact_sensitive_data

def test_safe_action_is_allowed():
    guardrails = Guardrails()
    action = Action(
        action=ActionType.CLICK,
        target=Target(name="Search"),
        risk_level=RiskLevel.SAFE,
    )
    guardrails.validate_action(action)

def test_risky_action_is_blocked():
    guardrails = Guardrails()
    action = Action(
        action=ActionType.CLICK,
        target=Target(name="Transfer Money"),
        risk_level=RiskLevel.RISKY,
    )

    with pytest.raises(GuardrailViolation):
        guardrails.validate_action(action)

def test_irreversible_action_is_blocked():
    guardrails = Guardrails()
    action = Action(
        action=ActionType.CLICK,
        target=Target(name="Delete Account"),
        risk_level=RiskLevel.IRREVERSIBLE,
    )

    with pytest.raises(GuardrailViolation):
        guardrails.validate_action(action)


def test_allowed_url_is_accepted():
    guardrails = Guardrails()

    guardrails.validate_url(
        "http://127.0.0.1:5000/search"
    )


def test_external_url_is_blocked():
    guardrails = Guardrails()

    with pytest.raises(GuardrailViolation):
        guardrails.validate_url(
            "https://example.com"
        )

def test_sensitive_data_is_redacted():
    data = {
        "member_id": "12345",
        "token": "secret-token",
        "status": "success",
    }

    result = redact_sensitive_data(data)

    assert result["member_id"] == "[REDACTED]"
    assert result["token"] == "[REDACTED]"
    assert result["status"] == "success"

def test_nested_sensitive_data_is_redacted():
    data = {
        "inputs": {
            "member_id": "12345"
        },
        "result": {
            "status": "success"
        }
    }

    result = redact_sensitive_data(data)

    assert result["inputs"]["member_id"] == "[REDACTED]"
    assert result["result"]["status"] == "success"