import pytest

from automation.capability.schema import Action, ActionType, RiskLevel, Target
from automation.safety.guardrails import Guardrails, GuardrailViolation, redact_sensitive_data


@pytest.mark.parametrize("url", [
    "http://127.0.0.1:5000.evil.example",
    "http://127.0.0.1:50001/search",
    "http://127.0.0.1:5000@evil.example",
    "http://user:secret@127.0.0.1:5000",
    "https://127.0.0.1:5000/search",
    "http://127.0.0.1:invalid",
    "http://[invalid",
    "file:///private.txt",
    "/search",
])
def test_disallowed_or_malformed_origins_are_blocked(url):
    with pytest.raises(GuardrailViolation):
        Guardrails().validate_url(url)


def test_configured_origin_uses_effective_port():
    guardrails = Guardrails(allowed_origins={"https://demo.example"})
    guardrails.validate_url("https://demo.example:443/search")
    with pytest.raises(GuardrailViolation):
        guardrails.validate_url("http://127.0.0.1:5000")


def test_empty_allowlist_blocks_all_origins():
    with pytest.raises(GuardrailViolation):
        Guardrails(allowed_origins=set()).validate_url("http://127.0.0.1:5000")

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
