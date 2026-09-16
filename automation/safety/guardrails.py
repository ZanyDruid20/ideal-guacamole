from urllib.parse import urlsplit
from contextlib import contextmanager

from automation.capability.schema import Action, ActionType, RiskLevel

class GuardrailViolation(Exception):
    pass

class Guardrails:
    def __init__(self, allowed_origins=None, allowed_click_names=None, allowed_input_labels=None):
        # Trusted application policy, not risk classifications supplied by the model.
        self.allowed_click_names = {"Search"} if allowed_click_names is None else set(allowed_click_names)
        self.allowed_input_labels = {"Member ID"} if allowed_input_labels is None else set(allowed_input_labels)
        self.allowed_action_types = {
            ActionType.TYPE,
            ActionType.CLICK,
            ActionType.EXTRACT, 
            ActionType.WAIT,
            ActionType.NAVIGATE,
        }

        origins = {"http://127.0.0.1:5000"} if allowed_origins is None else allowed_origins
        self.allowed_origins = {self._origin(url) for url in origins}

    @staticmethod
    def _origin(url: str) -> tuple[str, str, int]:
        try:
            parsed = urlsplit(url)
            if (
                parsed.scheme not in {"http", "https"}
                or not parsed.hostname
                or parsed.username is not None
                or parsed.password is not None
                or "\\" in url
                or any(character.isspace() for character in url)
            ):
                raise ValueError("Invalid application URL")
            port = parsed.port
            if port is None:
                port = 443 if parsed.scheme == "https" else 80
            return parsed.scheme, parsed.hostname, port
        except ValueError:
            raise GuardrailViolation("Invalid application URL") from None

    def validate_action(self, action: Action) -> None:
        if action.action not in self.allowed_action_types:
            raise GuardrailViolation(f"Action type '{action.action}' is not allowed ")
        if action.risk_level == RiskLevel.IRREVERSIBLE:
            raise GuardrailViolation("Irreversible actions require human approval")
        if action.risk_level == RiskLevel.RISKY:
            raise GuardrailViolation("Risky actions require human approval")
        if action.action == ActionType.CLICK and action.target.name not in self.allowed_click_names:
            raise GuardrailViolation("Button is not approved for replay")
        if action.action == ActionType.TYPE and action.target.label not in self.allowed_input_labels:
            raise GuardrailViolation("Input is not approved for replay")
        
    def validate_url(self, url: str) -> None:
        if self._origin(url) not in self.allowed_origins:
            raise GuardrailViolation(
                "URL is outside the allowed application"
            )

    def validate_discovery_action(self, action: dict) -> None:
        if not isinstance(action, dict):
            raise GuardrailViolation("Discovery action must be an object")
        action_type = action.get("action")
        if action_type == "done":
            return
        if not isinstance(action_type, str) or action_type not in self.allowed_action_types:
            raise GuardrailViolation("Discovery action type is not allowed")
        if action.get("risk_level", "safe") != "safe":
            raise GuardrailViolation("Risky actions require human approval")
        target = action.get("target", {})
        if not isinstance(target, dict):
            raise GuardrailViolation("Discovery target must be an object")
        if action_type == "click":
            name = target.get("name")
            if not isinstance(name, str) or name not in self.allowed_click_names:
                raise GuardrailViolation("Button is not approved for discovery")
        elif action_type == "type":
            label = target.get("label")
            if not isinstance(label, str) or label not in self.allowed_input_labels:
                raise GuardrailViolation("Input is not approved for discovery")
            if not isinstance(action.get("value"), str):
                raise GuardrailViolation("Typing requires a string value")
        elif action_type == "navigate":
            if not isinstance(action.get("value"), str):
                raise GuardrailViolation("Navigation requires a URL")
            self.validate_url(action["value"])
        elif action_type == "extract":
            row_id = target.get("id")
            if not isinstance(row_id, str) or not row_id.startswith("row_") or not row_id[4:].isdigit():
                raise GuardrailViolation("Extraction requires a valid row ID")
            if action.get("save_as") not in ("checking_balance", "savings_balance"):
                raise GuardrailViolation("Output is not approved for discovery")
        elif action_type == "wait":
            selector = target.get("selector")
            if selector is not None and not isinstance(selector, str):
                raise GuardrailViolation("Wait selector must be a string")

    @contextmanager
    def protect_context(self, context):
        """Guard requests, including redirect hops. Create context with service workers blocked."""
        def intercept(route):
            try:
                self.validate_url(route.request.url)
            except GuardrailViolation:
                route.abort("blockedbyclient")
                return
            try:
                # Do not let the fetch API follow a redirect outside policy.
                response = route.fetch(max_redirects=0)
                location = response.headers.get("location")
                if location and 300 <= response.status < 400:
                    from urllib.parse import urljoin
                    self.validate_url(urljoin(route.request.url, location))
                route.fulfill(response=response)
            except Exception:
                route.abort("blockedbyclient")
        def block_socket(socket):
            socket.close()
        context.route("**/*", intercept)
        context.route_web_socket("**/*", block_socket)
        try:
            yield
        finally:
            context.unroute("**/*", intercept)
        
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
