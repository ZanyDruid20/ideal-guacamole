from automation.capability.schema import Action, ActionType, RiskLevel

class GuardrailViolation(Exception):
    pass

class Guardrails:
    def __init__(self):
        self.allowed_action_types = {
            ActionType.TYPE,
            ActionType.CLICK,
            ActionType.EXTRACT, 
            ActionType.WAIT,
            ActionType.NAVIGATE,
        }

        self.allowed_url_prefixes = {
            "http://127.0.0.1:5000"
        }

    def validate_action(self, action: Action) -> None:
        if action.action not in self.allowed_action_types:
            raise GuardrailViolation(f"Action type '{action.action}' is not allowed ")
        if action.risk_level == RiskLevel.IRREVERSIBLE:
            raise GuardrailViolation("Irreversible actions require human approval")
        if action.risk_level == RiskLevel.RISKY:
            raise GuardrailViolation("Risky actions require human approval")
        
    def validate_url(self, url: str) -> None:
        if not any(
            url.startswith(prefix)
            for prefix in self.allowed_url_prefixes
        ):
            raise GuardrailViolation(
                f"URL '{url}' is outside the allowed application"
            )
        
def redact_sensitive_data(data):
    sensitive_fields = {
        "member_id",
        "password",
        "token",
        "access_token",
        "api_key",
    }

    if isinstance(data, dict):
        redacted = {}

        for key, value in data.items():
            if key.lower() in sensitive_fields:
                redacted[key] = "[REDACTED]"
            else:
                redacted[key] = redact_sensitive_data(value)

        return redacted

    if isinstance(data, list):
        return [
            redact_sensitive_data(item)
            for item in data
        ]

    return data