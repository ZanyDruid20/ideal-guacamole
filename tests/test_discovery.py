from unittest.mock import Mock, patch

import pytest

from automation.discovery import agent
from automation.safety.guardrails import Guardrails, GuardrailViolation


@pytest.fixture
def page():
    return Mock(url="http://127.0.0.1:5000")


@pytest.mark.parametrize("action", [
    {"action": "navigate", "value": "https://example.com"},
    {"action": "navigate", "value": "http://127.0.0.1:5000@evil.example"},
    {"action": "click", "target": {"name": "Transfer Money"}, "risk_level": "safe"},
    {"action": "click", "target": {"name": "Search"}, "risk_level": "risky"},
    {"action": "type", "target": {"label": "Password"}, "value": "secret"},
    {"action": "extract", "target": {"id": "row_0"}, "save_as": "password"},
    {"action": "extract", "target": {"id": "row_-1"}, "save_as": "savings_balance"},
    {"action": "execute_script"},
    {"action": []},
    {"action": "click", "target": None},
    [],
])
def test_blocked_action_never_interacts_with_browser(page, action):
    with pytest.raises(GuardrailViolation):
        agent.execute_action(page, action)
    assert page.mock_calls == []


def test_allowed_type_and_click_use_exact_targets(page):
    agent.execute_action(page, {
        "action": "type", "target": {"label": "Member ID"}, "value": "12345",
    })
    page.get_by_label.assert_called_once_with("Member ID", exact=True)
    page.get_by_label.return_value.fill.assert_called_once_with("12345")
    agent.execute_action(page, {"action": "click", "target": {"name": "Search"}})
    page.get_by_role.assert_called_once_with("button", name="Search", exact=True)


def test_configured_policy_is_honored(page):
    policy = Guardrails(allowed_click_names=set())
    with pytest.raises(GuardrailViolation):
        agent.execute_action(page, {"action": "click", "target": {"name": "Search"}}, policy)
    assert page.mock_calls == []


def test_disallowed_page_is_not_observed_or_sent_to_model(page):
    page.url = "https://example.com"
    with patch.object(agent, "observe_page") as observe, patch.object(agent, "decide_next_action") as decide:
        result = agent.run_discovery(page, "Read balances")
    assert result["status"] == "blocked"
    observe.assert_not_called()
    decide.assert_not_called()


def test_blocked_model_action_returns_context(page):
    with patch.object(agent, "observe_page", return_value={}), patch.object(
        agent, "decide_next_action", return_value={"action": "navigate", "value": "https://example.com"},
    ):
        result = agent.run_discovery(page, "Read balances")
    assert result["status"] == "blocked"
    assert result["step"] == 1
    assert result["actions"] == []
    assert result["outputs"] == {}
    page.goto.assert_not_called()


def test_redirect_stops_before_another_observation(page):
    def redirect(*args, **kwargs):
        page.url = "https://example.com"
    page.get_by_role.return_value.click.side_effect = redirect
    with patch.object(agent, "observe_page", return_value={}) as observe, patch.object(
        agent, "decide_next_action", return_value={"action": "click", "target": {"name": "Search"}},
    ) as decide:
        result = agent.run_discovery(page, "Read balances")
    assert result["status"] == "blocked"
    assert observe.call_count == decide.call_count == 1


def test_successful_discovery_preserves_actions_and_outputs_without_printing_values(page, capsys):
    actions = [
        {"action": "type", "target": {"label": "Member ID"}, "value": "private-id"},
        {"action": "click", "target": {"name": "Search"}},
        {"action": "extract", "target": {"id": "row_0"}, "save_as": "savings_balance"},
        {"action": "done"},
    ]
    page.locator.return_value.count.return_value = 1
    page.locator.return_value.nth.return_value.inner_text.return_value = "Savings $10"
    with patch.object(agent, "observe_page", return_value={"text": "private-text"}), patch.object(
        agent, "decide_next_action", side_effect=actions,
    ):
        result = agent.run_discovery(page, "Read savings")
    assert result["status"] == "success"
    assert result["actions"] == actions[:-1]
    assert result["outputs"] == {"savings_balance": "Savings $10"}
    console = capsys.readouterr().out
    assert "private-id" not in console
    assert "private-text" not in console
