import pytest 

from automation.capability.schema import (
    Action,
    ActionType,
    Capability,
    Checkpoint,
    CheckpointType,
    ExecutionResult,
    InputParameter,
    OutputParameter,
    ParameterType,
    ResultStatus,
    RetryPolicy,
    RiskLevel,
    Target,
)


# -------------------------
# Target tests
# -------------------------

def test_valid_target():
    target = Target(label="Member ID")
    assert target.label == "Member ID"


def test_empty_target_fails():
    with pytest.raises(ValueError):
        Target()


# -------------------------
# Checkpoint tests
# -------------------------

def test_visible_checkpoint_requires_target():
    with pytest.raises(ValueError):
        Checkpoint(
            condition=CheckpointType.VISIBLE
        )


def test_valid_visible_checkpoint():
    checkpoint = Checkpoint(
        condition=CheckpointType.VISIBLE,
        target=Target(name="Member Information"),
    )

    assert checkpoint.condition == CheckpointType.VISIBLE


def test_text_contains_requires_target_and_expected():
    with pytest.raises(ValueError):
        Checkpoint(
            condition=CheckpointType.TEXT_CONTAINS,
            target=Target(name="Member Status"),
        )


def test_url_contains_requires_expected():
    with pytest.raises(ValueError):
        Checkpoint(
            condition=CheckpointType.URL_CONTAINS
        )


def test_valid_url_contains():
    checkpoint = Checkpoint(
        condition=CheckpointType.URL_CONTAINS,
        expected="/member/",
    )

    assert checkpoint.expected == "/member/"


# -------------------------
# Action tests
# -------------------------

def test_valid_type_action():
    action = Action(
        action=ActionType.TYPE,
        target=Target(label="Member ID"),
        value="{{member_id}}",
    )

    assert action.value == "{{member_id}}"


def test_type_without_value_fails():
    with pytest.raises(ValueError):
        Action(
            action=ActionType.TYPE,
            target=Target(label="Member ID"),
        )


def test_click_without_target_fails():
    with pytest.raises(ValueError):
        Action(
            action=ActionType.CLICK
        )


def test_extract_without_save_as_fails():
    with pytest.raises(ValueError):
        Action(
            action=ActionType.EXTRACT,
            target=Target(selector="#savings-balance"),
        )


def test_valid_extract_action():
    action = Action(
        action=ActionType.EXTRACT,
        target=Target(selector="#savings-balance"),
        save_as="savings_balance",
    )

    assert action.save_as == "savings_balance"


def test_navigate_without_value_fails():
    with pytest.raises(ValueError):
        Action(
            action=ActionType.NAVIGATE
        )


def test_valid_navigate_action():
    action = Action(
        action=ActionType.NAVIGATE,
        value="http://localhost:5000",
    )

    assert action.value == "http://localhost:5000"


def test_wait_without_checkpoint_fails():
    with pytest.raises(ValueError):
        Action(
            action=ActionType.WAIT
        )


def test_valid_wait_action():
    action = Action(
        action=ActionType.WAIT,
        checkpoint=Checkpoint(
            condition=CheckpointType.VISIBLE,
            target=Target(name="Member Information"),
        ),
    )

    assert action.checkpoint is not None


# -------------------------
# Retry / risk tests
# -------------------------

def test_retry_policy_defaults():
    policy = RetryPolicy()

    assert policy.max_attempts == 1
    assert policy.delay_ms == 0


def test_action_default_risk_is_safe():
    action = Action(
        action=ActionType.CLICK,
        target=Target(name="Search Member"),
    )

    assert action.risk_level == RiskLevel.SAFE


# -------------------------
# Capability tests
# -------------------------

def test_valid_capability():
    capability = Capability(
        name="lookup_savings_balance",
        version="1.0",
        description="Look up a member's savings balance.",
        inputs=[
            InputParameter(
                name="member_id",
                type=ParameterType.STRING,
            )
        ],
        outputs=[
            OutputParameter(
                name="savings_balance",
                type=ParameterType.STRING,
            )
        ],
        actions=[
            Action(
                action=ActionType.TYPE,
                target=Target(label="Member ID"),
                value="{{member_id}}",
            ),
            Action(
                action=ActionType.CLICK,
                target=Target(name="Search Member"),
            ),
            Action(
                action=ActionType.EXTRACT,
                target=Target(selector="#savings-balance"),
                save_as="savings_balance",
            ),
        ],
        success_condition=Checkpoint(
            condition=CheckpointType.VISIBLE,
            target=Target(selector="#savings-balance"),
        ),
    )

    assert capability.name == "lookup_savings_balance"
    assert len(capability.actions) == 3
    assert capability.outputs[0].name == "savings_balance"


def test_undeclared_save_as_fails():
    with pytest.raises(ValueError):
        Capability(
            name="lookup_savings_balance",
            version="1.0",
            inputs=[
                InputParameter(
                    name="member_id",
                    type=ParameterType.STRING,
                )
            ],
            outputs=[
                OutputParameter(
                    name="savings_balance",
                    type=ParameterType.STRING,
                )
            ],
            actions=[
                Action(
                    action=ActionType.EXTRACT,
                    target=Target(selector="#savings-balance"),
                    save_as="wrong_output_name",
                )
            ],
            success_condition=Checkpoint(
                condition=CheckpointType.VISIBLE,
                target=Target(selector="#savings-balance"),
            ),
        )


# -------------------------
# ExecutionResult tests
# -------------------------

def test_success_execution_result():
    result = ExecutionResult(
        status=ResultStatus.SUCCESS,
        message="Balance extracted successfully.",
        outputs={
            "savings_balance": "$12,450.00"
        },
    )

    assert result.status == ResultStatus.SUCCESS
    assert result.outputs["savings_balance"] == "$12,450.00"


def test_hard_failure_execution_result():
    result = ExecutionResult(
        status=ResultStatus.HARD_FAILURE,
        step=2,
        message="Search button could not be found.",
        expected="Search Member button visible",
        observed="Search Member button missing",
    )

    assert result.status == ResultStatus.HARD_FAILURE
    assert result.step == 2