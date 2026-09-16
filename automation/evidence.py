import json
from datetime import datetime, timezone
from pathlib import Path

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
    
