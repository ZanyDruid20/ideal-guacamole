"""Deliberately require manual search, then resume saved balance extraction."""
from uuid import uuid4
from pathlib import Path

from automation.capability.schema import Action, ActionType
from automation.capability.serializer import load_capability
from automation.evidence import save_log
from automation.handoff.controller import HandoffController
from automation.replay.executor import ReplayExecutor
from automation.safety.session import protected_page
from automation.evidence import RunEvidence


def main():
    capability = load_capability(Path("evidence/artifacts/member_balances_v1.json"))
    # Controlled failure in an in-memory demo copy; the saved artifact is unchanged.
    capability.actions = [
        Action(action=ActionType.WAIT, checkpoint=capability.success_condition),
        *[action for action in capability.actions if action.action == ActionType.EXTRACT],
    ]
    controller = HandoffController()
    run_id = uuid4().hex
    evidence = RunEvidence("handoff")
    with protected_page() as page:
        page.set_default_timeout(3000)
        page.goto("http://127.0.0.1:5000")
        print("Demo: Accounts is absent on the search page, so the first checkpoint fails.")
        print("When paused, search for member 12345 in this browser, then type resume here.")
        result = ReplayExecutor(page, handoff=controller, evidence=evidence).execute(capability, {})
        save_log(f"replay_handoff_{run_id}.json", {
            "run_type": "controlled_replay_handoff",
            "capability": capability.name,
            "scenario": "Manual search required before balance extraction",
            "events": controller.events,
            "status": result.status.value,
            "step": result.step,
            "outputs_collected": list(result.outputs),
        })
        print(result.model_dump_json(indent=2))
        print(f"Evidence: evidence/logs/replay_handoff_{run_id}.json")


if __name__ == "__main__":
    main()
