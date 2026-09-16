from automation.capability.serializer import save_capability, load_capability
from automation.capability.schema import (
    Capability,
    InputParameter,
    OutputParameter,
    Action,
    ActionType,
    ParameterType,
    Target,
    Checkpoint,
    CheckpointType,
)


def test_save_and_load_capability(tmp_path):
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

    file_path = tmp_path / "lookup_savings_balance.json"

    save_capability(capability, file_path)

    assert file_path.exists()

    loaded_capability = load_capability(file_path)

    assert loaded_capability == capability
