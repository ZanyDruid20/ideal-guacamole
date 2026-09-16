from playwright.sync_api import Page, TimeoutError as BrowserTimeout
from automation.safety.guardrails import Guardrails, GuardrailViolation
from automation.handoff.controller import HandoffController
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
    def __init__(self, page: Page, guardrails: Guardrails | None = None,
                 handoff: HandoffController | None = None, evidence=None):
        self.page = page
        self.guardrails = guardrails if guardrails is not None else Guardrails()
        self.handoff = handoff
        self.evidence = evidence

    def _record(self, event, **details):
        if self.evidence is not None:
            self.evidence.record(event, **details)

    def _retry(self, operation, policy, step):
        attempts = policy.max_attempts if policy else 1
        for attempt in range(1, attempts + 1):
            try:
                return operation()
            except BrowserTimeout:
                self._record("recoverable_failure", step=step, attempt=attempt,
                             reason="read_or_wait_timeout")
                if attempt == attempts:
                    raise
                self.guardrails.validate_url(self.page.url)
                self.page.wait_for_timeout(policy.delay_ms)

    def execute(self, capability: Capability, inputs: dict) -> ExecutionResult:
        outputs = {}

        for step, action in enumerate(capability.actions, start=1):
            action_completed = False
            try:
                self._record("step_started", step=step, action=action.action.value)
                self.guardrails.validate_url(self.page.url)
                self.guardrails.validate_action(action)
                if action.action == ActionType.NAVIGATE:
                    destination = self._resolve_value(action.value, inputs)
                    self.guardrails.validate_url(destination)

                if action.action in (ActionType.WAIT, ActionType.EXTRACT):
                    result = self._retry(lambda: self._execute_action(action, inputs), action.retry_policy, step)
                else:
                    result = self._execute_action(action, inputs)
                action_completed = True
                self.guardrails.validate_url(self.page.url)

                if action.save_as is not None:
                    outputs[action.save_as] = result

                # Detect expected business outcome
                if action.action == ActionType.CLICK:
                    body_text = self.page.locator("body").inner_text()

                    if "Member not found" in body_text:
                        self._record("business_outcome", step=step, reason="member_not_found")
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
                self._record("step_completed", step=step)

            except Exception as error:
                if self.evidence is not None:
                    self.evidence.failure(self.page, step, error)
                # Only skip a step when its explicit postcondition can be verified.
                # Never repeat a click or turn human resume into policy approval.
                if (self.handoff is not None and not isinstance(error, GuardrailViolation)
                        and action.checkpoint is not None
                        and (action_completed or action.action == ActionType.WAIT)):
                    if self._request_handoff(capability, step, action.checkpoint):
                        continue
                    return ExecutionResult(
                        status=ResultStatus.ESCALATION_REQUIRED, step=step,
                        message="Operator aborted handoff; replay stopped.", outputs=outputs,
                    )
                return ExecutionResult(
                    status=ResultStatus.HARD_FAILURE,
                    step=step,
                    message=str(error),
                    expected=action.checkpoint.condition.value if action.checkpoint else f"{action.action.value} completes within policy",
                    observed=type(error).__name__,
                    outputs=outputs,
                )

        # Verify the capability's final success condition
        try:
            self.guardrails.validate_url(self.page.url)
            self._check_checkpoint(capability.success_condition)

        except Exception as error:
            if self.evidence is not None:
                self.evidence.failure(self.page, len(capability.actions), error)
            if self.handoff is not None and not isinstance(error, GuardrailViolation):
                if self._request_handoff(capability, len(capability.actions), capability.success_condition):
                    return ExecutionResult(status=ResultStatus.SUCCESS, outputs=outputs)
                return ExecutionResult(
                    status=ResultStatus.ESCALATION_REQUIRED, step=len(capability.actions),
                    message="Operator aborted handoff; replay stopped.", outputs=outputs,
                )
            return ExecutionResult(
                status=ResultStatus.HARD_FAILURE,
                step=len(capability.actions),
                message=str(error),
                expected=capability.success_condition.condition.value,
                observed=type(error).__name__,
                outputs=outputs,
            )

        return ExecutionResult(
            status=ResultStatus.SUCCESS,
            outputs=outputs,
        )
    
    def _request_handoff(self, capability, step, checkpoint):
        def verify():
            self.guardrails.validate_url(self.page.url)
            self._check_checkpoint(checkpoint)
            self.guardrails.validate_url(self.page.url)

        self._record("handoff_requested", step=step, checkpoint=checkpoint.condition.value)
        resumed = self.handoff.intervene(
            page=self.page, capability=capability.name, step=step,
            reason=f"Checkpoint {checkpoint.condition.value} failed; correct the page to satisfy {checkpoint.expected or 'the target visibility condition'}.",
            verify=verify,
        )
        self._record("handoff_resumed" if resumed else "handoff_aborted", step=step)
        return resumed

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
        
