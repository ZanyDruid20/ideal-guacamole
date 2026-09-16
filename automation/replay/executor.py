from playwright.sync_api import Page
from automation.capability.schema import (
    Capability,
    Action,
    ActionType,
    Checkpoint,
    CheckpointType,
    ExecutionResult,
    ResultStatus,
)

class ReplayExecutor:
    def __init__(self, page):
        self.page = page

    def execute(self, capability: Capability, inputs: dict) -> ExecutionResult:
        outputs = {}

        for step, action in enumerate(capability.actions, start=1):
            try:
                result = self._execute_action(action, inputs)

                if action.save_as is not None:
                    outputs[action.save_as] = result

                # Detect expected business outcome
                if action.action == ActionType.CLICK:
                    body_text = self.page.locator("body").inner_text()

                    if "Member not found" in body_text:
                        return ExecutionResult(
                            status=ResultStatus.BUSINESS_OUTCOME,
                            step=step,
                            message="Member not found",
                            observed="Member not found",
                            outputs=outputs,
                        )

                # Verify checkpoint attached to this action
                if (
                    action.checkpoint is not None
                    and action.action != ActionType.WAIT
                ):
                    self._check_checkpoint(action.checkpoint)

            except Exception as error:
                return ExecutionResult(
                    status=ResultStatus.HARD_FAILURE,
                    step=step,
                    message=str(error),
                    outputs=outputs,
                )

        # Verify the capability's final success condition
        try:
            self._check_checkpoint(capability.success_condition)

        except Exception as error:
            return ExecutionResult(
                status=ResultStatus.HARD_FAILURE,
                step=len(capability.actions),
                message=str(error),
                outputs=outputs,
            )

        return ExecutionResult(
            status=ResultStatus.SUCCESS,
            outputs=outputs,
        )
    
    def _execute_action(
        self,
        action: Action,
        inputs: dict
    ):
        if action.action == ActionType.TYPE:
            value = self._resolve_value(action.value, inputs)
            self.page.get_by_label(action.target.label).fill(value)
        elif action.action == ActionType.CLICK:
            self.page.get_by_role(
                "button",
                name=action.target.name
            ).click()

        elif action.action == ActionType.EXTRACT:
            element = self.page.locator(
                action.target.selector
            )

            return element.inner_text()

        elif action.action == ActionType.NAVIGATE:
            value = self._resolve_value(action.value, inputs)
            self.page.goto(value)

        elif action.action == ActionType.WAIT:
            self._check_checkpoint(action.checkpoint)

        else:
            raise ValueError(
                f"Unsupported action: {action.action}"
            )

        return None
    def _resolve_value(self, value: str, inputs: dict) -> str:
        if value.startswith("{{") and value.endswith("}}"):
            input_name = value[2:-2]
    
            if input_name not in inputs:
                raise ValueError(
                    f"Missing required input: {input_name}"
                )
    
            return str(inputs[input_name])
    
        return value
    def _check_checkpoint(
        self,
        checkpoint: Checkpoint
    ) -> None:
        if checkpoint.condition == CheckpointType.VISIBLE:
            self.page.locator(
                checkpoint.target.selector
            ).wait_for(state="visible")

        elif checkpoint.condition == CheckpointType.NOT_VISIBLE:
            self.page.locator(
                checkpoint.target.selector
            ).wait_for(state="hidden")

        elif checkpoint.condition == CheckpointType.URL_CONTAINS:
            if checkpoint.expected not in self.page.url:
                raise ValueError(
                    f"Expected URL to contain "
                    f"'{checkpoint.expected}', "
                    f"observed '{self.page.url}'"
                )

        elif checkpoint.condition == CheckpointType.TEXT_CONTAINS:
            text = self.page.locator(
                checkpoint.target.selector
            ).inner_text()

            if checkpoint.expected not in text:
                raise ValueError(
                    f"Expected text to contain "
                    f"'{checkpoint.expected}', "
                    f"observed '{text}'"
                )

        else:
            raise ValueError(
                f"Unsupported checkpoint: "
                f"{checkpoint.condition}"
            )
        
