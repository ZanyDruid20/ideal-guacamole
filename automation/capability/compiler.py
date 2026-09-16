from automation.capability.schema import (
    Capability,
    Action,
    ActionType,
    Target,
    InputParameter,
    OutputParameter,
    ParameterType,
    Checkpoint,
    CheckpointType,
)


def compile_member_balance_capability(
    discovery_result: dict,
) -> Capability:
    """
    Convert a successful discovery run into a reusable,
    deterministic capability for retrieving member balances.
    """
    # Reject discovery runs that did not funush successfully
    if discovery_result.get("status") != "success":
        raise ValueError(
            "Cannot compile an unsuccessful discovery run"
        )
    # read the actions and reject an empty workfloe
    discovered_actions = discovery_result.get("actions", [])

    if not discovered_actions:
        raise ValueError(
            "Discovery result contains no actions"
        )
    # Build replay actions in the same order as the discovery actions.
    actions = []

    for discovered_action in discovered_actions:
        action_type = discovered_action.get("action")

        if action_type == "type":
            actions.append(
                Action(
                    action=ActionType.TYPE,
                    target=Target(
                        label="Member ID"
                    ),
                    value="{{member_id}}",
                )
            )

        elif action_type == "click":
            actions.append(
                Action(
                    action=ActionType.CLICK,
                    target=Target(
                        name="Search"
                    ),
                    checkpoint=Checkpoint(
                        condition=CheckpointType.URL_CONTAINS,
                        expected="/search",
                    ),
                )
            )

        elif action_type == "extract":
            save_as = discovered_action.get("save_as")

            if save_as == "checking_balance":
                actions.append(
                    Action(
                        action=ActionType.EXTRACT,
                        target=Target(
                            selector=(
                                'tbody tr:has-text("checking") '
                                'td:nth-child(3)'
                            )
                        ),
                        save_as="checking_balance",
                    )
                )

            elif save_as == "savings_balance":
                actions.append(
                    Action(
                        action=ActionType.EXTRACT,
                        target=Target(
                            selector=(
                                'tbody tr:has-text("savings") '
                                'td:nth-child(3)'
                            )
                        ),
                        save_as="savings_balance",
                    )
                )

            else:
                raise ValueError(
                    f"Unknown discovered output: {save_as}"
                )

        else:
            raise ValueError(
                f"Unsupported discovered action: {action_type}"
            )

    return Capability(
        name="get_member_balances",
        version="1.0.0",
        description=(
            "Find a member by member ID and return "
            "their checking and savings balances."
        ),
        inputs=[
            InputParameter(
                name="member_id",
                type=ParameterType.STRING,
                required=True,
                description="Member ID to search for.",
            )
        ],
        outputs=[
            OutputParameter(
                name="checking_balance",
                type=ParameterType.STRING,
                description="Member checking account balance.",
            ),
            OutputParameter(
                name="savings_balance",
                type=ParameterType.STRING,
                description="Member savings account balance.",
            ),
        ],
        actions=actions,
        success_condition=Checkpoint(
            condition=CheckpointType.TEXT_CONTAINS,
            target=Target(
                selector="body"
            ),
            expected="Accounts",
        ),
    )