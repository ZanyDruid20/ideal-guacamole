from unittest.mock import create_autospec, patch

import pytest
from playwright.sync_api import Locator, Page, TimeoutError

from automation.capability.schema import (
    Action, ActionType, Capability, Checkpoint, CheckpointType,
    InputParameter, OutputParameter, ParameterType, ResultStatus, RiskLevel, Target,
)
from automation.replay.executor import ReplayExecutor
from automation.safety.guardrails import Guardrails
from automation.handoff.controller import HandoffController


def test_failed_checkpoint_hands_off_and_continues_without_repeating_click(browser_page, capability):
    page, elements = browser_page
    capability.actions[2].checkpoint = Checkpoint(condition=CheckpointType.URL_CONTAINS, expected="/accounts")
    controller = HandoffController()
    answers = iter(["resume", "Opened accounts manually"])
    def operator(prompt):
        assert controller.is_human_controlled()
        elements["#checking"].inner_text.assert_not_called()
        page.url = "http://127.0.0.1:5000/accounts"
        return next(answers)
    with patch("builtins.input", side_effect=operator):
        result = ReplayExecutor(page, handoff=controller).execute(capability, {"member_id": "12345"})
    assert result.status == ResultStatus.SUCCESS
    assert result.outputs["checking_balance"] == "$100.00"
    page.get_by_role.return_value.click.assert_called_once_with()
    assert not controller.active
    assert [event["event"] for event in controller.events] == ["requested", "resumed"]


def test_unfixed_checkpoint_remains_paused_and_abort_stops_extraction(browser_page, capability):
    page, elements = browser_page
    capability.actions[2].checkpoint = Checkpoint(condition=CheckpointType.URL_CONTAINS, expected="/accounts")
    controller = HandoffController()
    with patch("builtins.input", side_effect=["resume", "Tried fixing page", "abort"]):
        result = ReplayExecutor(page, handoff=controller).execute(capability, {"member_id": "12345"})
    assert result.status == ResultStatus.ESCALATION_REQUIRED
    elements["#checking"].inner_text.assert_not_called()
    assert [event["event"] for event in controller.events] == ["requested", "verification_failed", "aborted"]


def test_policy_failure_cannot_be_overridden_by_handoff(browser_page, capability):
    page, _ = browser_page
    capability.actions[0].value = "https://example.com"
    controller = HandoffController()
    with patch("builtins.input") as prompt:
        result = ReplayExecutor(page, handoff=controller).execute(capability, {})
    assert result.status == ResultStatus.HARD_FAILURE
    prompt.assert_not_called()
    page.goto.assert_not_called()


def test_final_checkpoint_handoff_verifies_before_success(browser_page, capability):
    page, elements = browser_page
    elements["body"].inner_text.side_effect = ["Accounts", "Expired", "Accounts"]
    controller = HandoffController()
    with patch("builtins.input", side_effect=["resume", "Restored accounts page"]):
        result = ReplayExecutor(page, handoff=controller).execute(capability, {"member_id": "12345"})
    assert result.status == ResultStatus.SUCCESS
    assert elements["body"].inner_text.call_count == 3


def test_wait_checkpoint_can_resume_after_manual_correction(browser_page, capability):
    page, elements = browser_page
    capability.actions.insert(0, Action(
        action=ActionType.WAIT,
        checkpoint=Checkpoint(condition=CheckpointType.VISIBLE, target=Target(selector="#ready")),
    ))
    elements["#ready"].wait_for.side_effect = [TimeoutError("Not ready"), None]
    with patch("builtins.input", side_effect=["resume", "Made page ready"]):
        result = ReplayExecutor(page, handoff=HandoffController()).execute(capability, {"member_id": "12345"})
    assert result.status == ResultStatus.SUCCESS
    assert elements["#ready"].wait_for.call_count == 2


@pytest.mark.parametrize("value,inputs", [
    ("https://example.com", {}),
    ("{{destination}}", {"destination": "https://example.com"}),
])
def test_external_navigation_is_blocked_before_goto(browser_page, capability, value, inputs):
    page, _ = browser_page
    capability.actions[0].value = value
    result = ReplayExecutor(page).execute(capability, inputs)
    assert result.status == ResultStatus.HARD_FAILURE
    assert result.step == 1
    assert "outside the allowed application" in result.message
    page.goto.assert_not_called()
    page.get_by_label.assert_not_called()


@pytest.mark.parametrize("risk", [RiskLevel.RISKY, RiskLevel.IRREVERSIBLE])
def test_risky_click_is_blocked_before_browser_interaction(browser_page, capability, risk):
    page, _ = browser_page
    capability.actions[2].risk_level = risk
    result = ReplayExecutor(page).execute(capability, {"member_id": "12345"})
    assert result.status == ResultStatus.HARD_FAILURE
    assert result.step == 3
    page.get_by_role.assert_not_called()


def test_disallowed_current_page_blocks_execution(browser_page, capability):
    page, _ = browser_page
    page.url = "https://example.com"
    result = ReplayExecutor(page).execute(capability, {"member_id": "12345"})
    assert result.status == ResultStatus.HARD_FAILURE
    page.goto.assert_not_called()


def test_external_redirect_stops_before_next_action(browser_page, capability):
    page, _ = browser_page
    def redirect(url):
        page.url = "https://example.com"
    page.goto.side_effect = redirect
    result = ReplayExecutor(page).execute(capability, {"member_id": "12345"})
    assert result.status == ResultStatus.HARD_FAILURE
    assert result.step == 1
    page.get_by_label.assert_not_called()


def test_executor_honors_supplied_action_policy(browser_page, capability):
    page, _ = browser_page
    policy = Guardrails()
    policy.allowed_action_types.remove(ActionType.NAVIGATE)
    result = ReplayExecutor(page, guardrails=policy).execute(capability, {})
    assert result.status == ResultStatus.HARD_FAILURE
    page.goto.assert_not_called()


@pytest.fixture
def browser_page():
    page = create_autospec(Page, instance=True)
    selectors = ("body", "#checking", "#savings", "#ready")
    elements = {
        selector: create_autospec(Locator, instance=True)
        for selector in selectors
    }
    page.locator.side_effect = elements.__getitem__
    page.get_by_label.return_value = create_autospec(Locator, instance=True)
    page.get_by_role.return_value = create_autospec(Locator, instance=True)
    page.url = "http://127.0.0.1:5000/search"
    elements["body"].inner_text.return_value = "Accounts"
    elements["#checking"].inner_text.return_value = "$100.00"
    elements["#savings"].inner_text.return_value = "$250.00"
    return page, elements


@pytest.fixture
def capability():
    return Capability(
        name="member_balances",
        version="1.0",
        inputs=[InputParameter(name="member_id", type=ParameterType.STRING)],
        outputs=[
            OutputParameter(name=name, type=ParameterType.STRING)
            for name in ("checking_balance", "savings_balance")
        ],
        actions=[
            Action(action=ActionType.NAVIGATE, value="http://127.0.0.1:5000"),
            Action(
                action=ActionType.TYPE,
                target=Target(label="Member ID"), value="{{member_id}}",
            ),
            Action(action=ActionType.CLICK, target=Target(name="Search")),
            Action(
                action=ActionType.EXTRACT, target=Target(selector="#checking"),
                save_as="checking_balance",
            ),
            Action(
                action=ActionType.EXTRACT, target=Target(selector="#savings"),
                save_as="savings_balance",
            ),
        ],
        success_condition=Checkpoint(
            condition=CheckpointType.TEXT_CONTAINS,
            target=Target(selector="body"), expected="Accounts",
        ),
    )


def test_success_returns_balances_and_uses_member_input(browser_page, capability):
    page, _ = browser_page

    result = ReplayExecutor(page).execute(capability, {"member_id": "12345"})

    assert result.status == ResultStatus.SUCCESS
    assert result.outputs == {"checking_balance": "$100.00", "savings_balance": "$250.00"}
    page.goto.assert_called_once_with("http://127.0.0.1:5000")
    page.get_by_label.assert_called_once_with("Member ID")
    page.get_by_label.return_value.fill.assert_called_once_with("12345")
    page.get_by_role.assert_called_once_with("button", name="Search")
    page.get_by_role.return_value.click.assert_called_once_with()


def test_missing_input_stops_before_typing(browser_page, capability):
    page, elements = browser_page

    result = ReplayExecutor(page).execute(capability, {})

    assert result.status == ResultStatus.HARD_FAILURE
    assert result.step == 2
    assert result.message == "Missing required input: member_id"
    assert result.outputs == {}
    page.get_by_label.assert_not_called()
    page.get_by_role.assert_not_called()
    elements["#checking"].inner_text.assert_not_called()


def test_action_failure_preserves_previous_outputs(browser_page, capability):
    page, elements = browser_page
    elements["#savings"].inner_text.side_effect = TimeoutError("Savings element missing")

    result = ReplayExecutor(page).execute(capability, {"member_id": "12345"})

    assert result.status == ResultStatus.HARD_FAILURE
    assert result.step == 5
    assert result.message == "Savings element missing"
    assert result.outputs == {"checking_balance": "$100.00"}
    # Only the post-click business-outcome check ran, not the final check.
    assert elements["body"].inner_text.call_count == 1


def test_member_not_found_returns_business_outcome(browser_page, capability):
    page, elements = browser_page
    elements["body"].inner_text.return_value = "Member not found."

    result = ReplayExecutor(page).execute(capability, {"member_id": "unknown"})

    assert result.status == ResultStatus.BUSINESS_OUTCOME
    assert result.step == 3
    assert result.message == "Member not found"
    assert result.observed == "Member not found"
    assert result.outputs == {}
    elements["#checking"].inner_text.assert_not_called()
    elements["#savings"].inner_text.assert_not_called()
    assert elements["body"].inner_text.call_count == 1


def test_attached_checkpoint_failure_stops_next_action(browser_page, capability):
    page, elements = browser_page
    capability.actions[2].checkpoint = Checkpoint(
        condition=CheckpointType.URL_CONTAINS, expected="/accounts",
    )

    result = ReplayExecutor(page).execute(capability, {"member_id": "12345"})

    assert result.status == ResultStatus.HARD_FAILURE
    assert result.step == 3
    assert "/accounts" in result.message
    assert page.url in result.message
    elements["#checking"].inner_text.assert_not_called()


def test_final_success_condition_is_checked_after_actions(browser_page, capability):
    page, elements = browser_page
    elements["body"].inner_text.side_effect = ["Accounts", "Session expired"]

    result = ReplayExecutor(page).execute(capability, {"member_id": "12345"})

    assert result.status == ResultStatus.HARD_FAILURE
    assert result.step == 5
    assert "Accounts" in result.message
    assert "Session expired" in result.message
    assert result.outputs == {"checking_balance": "$100.00", "savings_balance": "$250.00"}
    assert elements["body"].inner_text.call_count == 2


@pytest.mark.parametrize(
    "condition,state",
    [(CheckpointType.VISIBLE, "visible"), (CheckpointType.NOT_VISIBLE, "hidden")],
)
def test_wait_checks_visibility_once(browser_page, capability, condition, state):
    page, elements = browser_page
    capability.actions.insert(0, Action(
        action=ActionType.WAIT,
        checkpoint=Checkpoint(condition=condition, target=Target(selector="#ready")),
    ))

    result = ReplayExecutor(page).execute(capability, {"member_id": "12345"})

    assert result.status == ResultStatus.SUCCESS
    elements["#ready"].wait_for.assert_called_once_with(state=state)
