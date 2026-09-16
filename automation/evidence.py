import json
from datetime import datetime, timezone
from pathlib import Path
from uuid import uuid4

from automation.safety.guardrails import redact_sensitive_data

LOG_DIR = Path("evidence/logs")
SCREENSHOT_DIR = Path("evidence/screenshots")

def save_log(filename: str, data: dict) -> None:
    LOG_DIR.mkdir(parents=True, exist_ok=True)
    safe_data = redact_sensitive_data(data)
    safe_data["timestamp"] = datetime.now(timezone.utc).isoformat()
    path = LOG_DIR / filename
    path.write_text(json.dumps(safe_data, indent=2))

def save_screenshot(page, filename: str) -> None:
    SCREENSHOT_DIR.mkdir(parents=True, exist_ok=True)
    page.screenshot(path=str(SCREENSHOT_DIR / filename), full_page=True)


class RunEvidence:
    """Persist structural diagnostics, never page text, input values, or exception text."""
    def __init__(self, run_type, root=Path("evidence/runs")):
        self.directory = root / f"{run_type}_{uuid4().hex}"
        self.directory.mkdir(parents=True, exist_ok=True)
        self.events = []

    def record(self, event, **details):
        self.events.append({"timestamp": datetime.now(timezone.utc).isoformat(),
                            "event": event, **details})
        (self.directory / "events.json").write_text(
            json.dumps(redact_sensitive_data(self.events), indent=2), encoding="utf-8")

    def failure(self, page, step, error):
        # A deliberately reduced DOM snapshot: no text, attributes, URLs or values.
        try:
            structure = page.evaluate("""() => {
                const counts = {};
                for (const e of document.querySelectorAll('*')) {
                    const tag = e.tagName.toLowerCase();
                    counts[tag] = (counts[tag] || 0) + 1;
                }
                return {ready_state: document.readyState, element_counts: counts};
            }""")
            filename = f"failure_{len(self.events)}.json"
            (self.directory / filename).write_text(json.dumps(structure, indent=2), encoding="utf-8")
            self.record("failure", step=step, error_type=type(error).__name__, snapshot=filename)
        except Exception as capture_error:
            self.record("failure", step=step, error_type=type(error).__name__,
                        capture_error=type(capture_error).__name__)
    
