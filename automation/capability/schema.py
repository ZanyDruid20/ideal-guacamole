from typing import Optional, List
from pydantic import BaseModel, model_validator, Field
from enum import Enum

# Defines the supported automated actions
class ActionType(str, Enum):
    TYPE = "type"
    CLICK = "click"
    EXTRACT = "extract"
    WAIT = "wait"
    NAVIGATE = "navigate"
# Defines the verifiability of conditions that can be checked during execution
class CheckpointType(str, Enum):
    VISIBLE = "visible"
    NOT_VISIBLE = "not_visible"
    URL_CONTAINS = "url_contains"
    TEXT_CONTAINS = "text_contains"
# Defines the data types for inputs and outputs
class ParameterType(str, Enum):
    STRING = "string"
    INTEGER = "integer"
    BOOLEAN = "boolean"
    NUMBER = "number"
# Classifies the action risk levels for safety levels
class RiskLevel(str, Enum):
    SAFE = "safe"
    RISKY = "risky"
    IRREVERSIBLE = "irreversible"
# Possible results from an action
class ResultStatus(str, Enum):
    SUCCESS = "success"
    BUSINESS_OUTCOME = "business_outcome"
    RECOVERABLE_FAILURE = "recoverable_failure"
    HARD_FAILURE = "hard_failure"
    ESCALATION_REQUIRED = "escalation_required"
# Describes how to locare a UI element and requires at least one targeting field
class Target(BaseModel):
    role: Optional[str] = None
    label: Optional[str] = None
    name: Optional[str] = None
    selector: Optional[str] = None
    @model_validator(mode="after")
    def validate_target(self):
        if (
            self.role is None
            and self.label is None
            and self.name is None
            and self.selector is None
        ):
            raise ValueError("Target requires at least one targeting field")
        return self
# Describes a condition to verify and validates it.
class Checkpoint(BaseModel):
    condition: CheckpointType
    target: Optional[Target] = None
    expected: Optional[str] = None
    @model_validator(mode="after")
    def validate_checkpoint(self):
        if self.condition in (
        CheckpointType.VISIBLE,
        CheckpointType.NOT_VISIBLE
        ):
            if self.target is None:
                raise ValueError("VISIBLE and NOT_VISIBLE checkpoints require a target")
        if self.condition == CheckpointType.TEXT_CONTAINS:
            if self.target is None or self.expected is None:
                raise ValueError("TEXT_CONTAINS checkpoint requires both a target and expected text")
        if self.condition == CheckpointType.URL_CONTAINS:
            if self.expected is None:
                raise ValueError("URL_CONTAINS checkpoint requires expected text")
        return self
# Stores the retry settings that the program must execute when there are issues
class RetryPolicy(BaseModel):
    max_attempts: int = 1
    delay_ms: int = 0

# This describes the actions the program can take
class Action(BaseModel):
    action: ActionType
    target: Optional[Target] = None
    value: Optional[str] = None
    checkpoint: Optional[Checkpoint] = None
    retry_policy: Optional[RetryPolicy] = None
    save_as: Optional[str] = None
    risk_level: RiskLevel = RiskLevel.SAFE
    @model_validator(mode="after")
    def validate_action(self):
        if self.action == ActionType.TYPE:
            if self.target is None or self.value is None:
                raise ValueError("TYPE action requires both a target and a value")
        if self.action == ActionType.CLICK:
            if self.target is None:
                raise ValueError("CLICK action requires a target")
        if self.action == ActionType.EXTRACT:
            if self.target is None or self.save_as is None:
                raise ValueError("EXTRACT action requires a target and save_as")
        if self.action == ActionType.NAVIGATE:
            if self.value is None:
                raise ValueError("NAVIGATE action requires a value")
        if self.action == ActionType.WAIT:
            if self.checkpoint is None:
                raise ValueError("WAIT action requires a checkpoint")
        return self
# Describes an input accepted by the capability
class InputParameter(BaseModel):
    name: str
    type: ParameterType
    required: bool = True
    description: Optional[str] = None
# Described a named output that the capability is expected to produce
class OutputParameter(BaseModel):
    name: str
    type: ParameterType
    description: Optional[str] = None
# Groups workflow metadata, parameters, actions, and the final success condition.
# Validates that extracted values use declared output names.
class Capability(BaseModel):
    name: str
    version: str
    description: Optional[str] = None
    inputs: List[InputParameter]
    outputs: List[OutputParameter]
    actions: List[Action]
    success_condition: Checkpoint
    @model_validator(mode="after")
    def validate_capability(self):
        output_names = {output.name for output in self.outputs}
        for action in self.actions:
            if action.save_as is not None and action.save_as not in output_names:
                raise ValueError(f"Action save_as '{action.save_as}' is not a declared output")
        return self
# Stores the execution status, diagnostic details, and collected outputs.
class ExecutionResult(BaseModel):
    status: ResultStatus
    step: Optional[int] = None
    message: Optional[str] = None
    expected: Optional[str] = None 
    observed: Optional[str] = None
    outputs: dict[str, str] = Field(default_factory=dict)