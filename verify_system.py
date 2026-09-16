"""Headless, offline browser checks against local servers; no model calls."""
from pathlib import Path
from threading import Thread
from unittest.mock import patch

from flask import Flask, redirect
from werkzeug.serving import make_server

from mock_app.app import app
from automation.capability.serializer import load_capability
from automation.capability.schema import Action, ActionType, Checkpoint, CheckpointType, Target, RetryPolicy
from automation.evidence import RunEvidence
from automation.handoff.controller import HandoffController
from automation.replay.executor import ReplayExecutor
from automation.safety.guardrails import Guardrails
from automation.safety.session import protected_page


def main():
    outside = Flask("outside")
    hits = []
    @outside.route("/")
    def outside_index():
        hits.append(True)
        return "must not be reached"
    external = make_server("127.0.0.1", 0, outside)
    external_url = f"http://127.0.0.1:{external.server_port}/"
    app.add_url_rule("/test-redirect", "test_redirect", lambda: redirect(external_url))
    server = make_server("127.0.0.1", 0, app)
    origin = f"http://127.0.0.1:{server.server_port}"
    for item in (server, external):
        Thread(target=item.serve_forever, daemon=True).start()
    evidence = RunEvidence("offline_browser_verification")
    policy = Guardrails(allowed_origins={origin})
    capability = load_capability(Path("evidence/artifacts/member_balances_v1.json"))
    try:
        with protected_page(policy, headless=True) as page:
            page.goto(origin)
            result = ReplayExecutor(page, policy, evidence=evidence).execute(capability, {"member_id": "67890"})
            assert result.status == "success", result
            assert set(result.outputs) == {"checking_balance", "savings_balance"}
            evidence.record("verified", scenario="successful_replay")

            page.goto(origin)
            result = ReplayExecutor(page, policy, evidence=evidence).execute(capability, {"member_id": "unknown"})
            assert result.status == "business_outcome", result
            evidence.record("verified", scenario="not_found")

            try:
                page.goto(origin + "/test-redirect")
            except Exception:
                pass
            assert not hits, "External redirect reached the forbidden server"
            evidence.record("verified", scenario="external_redirect_blocked", external_requests=len(hits))

            # A blocked navigation can leave Chromium's error-page navigation pending.
            page = page.context.new_page()
            page.goto(origin)
            page.set_default_timeout(50)
            # First read timeout, then element appears during the bounded retry delay.
            page.evaluate("setTimeout(() => {const e=document.createElement('div'); e.id='ready'; e.textContent='Ready'; document.body.append(e)}, 200)")
            transient = capability.model_copy(deep=True)
            transient.actions = [Action(action=ActionType.WAIT,
                checkpoint=Checkpoint(condition=CheckpointType.VISIBLE, target=Target(selector="#ready")),
                retry_policy=RetryPolicy(max_attempts=2, delay_ms=300))]
            transient.success_condition = Checkpoint(condition=CheckpointType.URL_CONTAINS, expected=origin)
            transient.outputs = []
            result = ReplayExecutor(page, policy, evidence=evidence).execute(transient, {})
            assert result.status == "success", result
            assert any(e["event"] == "recoverable_failure" for e in evidence.events)
            evidence.record("verified", scenario="bounded_recovery")

            page.set_default_timeout(1000)
            page.goto(origin)
            manual = capability.model_copy(deep=True)
            manual.actions = [Action(action=ActionType.WAIT, checkpoint=capability.success_condition),
                              *[a for a in capability.actions if a.action == ActionType.EXTRACT]]
            controller = HandoffController()
            def operator(prompt):
                if prompt.startswith("Type"):
                    page.get_by_label("Member ID").fill("12345")
                    page.get_by_role("button", name="Search", exact=True).click()
                    return "resume"
                return "Automated test operator completed search in the same page"
            with patch("builtins.input", side_effect=operator):
                result = ReplayExecutor(page, policy, controller, evidence).execute(manual, {})
            assert result.status == "success", result
            evidence.record("verified", scenario="same_page_handoff", operator="automated_test")
            assert list(evidence.directory.glob("failure_*.json"))
            page.goto(origin)
            with patch("builtins.input", return_value="abort"):
                result = ReplayExecutor(page, policy, HandoffController(), evidence).execute(manual, {})
            assert result.status == "escalation_required", result
            assert result.outputs == {}
            evidence.record("verified", scenario="handoff_abort")
        print(f"All 6 browser scenarios passed. Evidence: {evidence.directory}")
    finally:
        server.shutdown()
        external.shutdown()


if __name__ == "__main__":
    main()
