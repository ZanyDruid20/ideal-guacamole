import argparse
from pathlib import Path

from automation.capability.serializer import load_capability
from automation.evidence import RunEvidence
from automation.handoff.controller import HandoffController
from automation.replay.executor import ReplayExecutor
from automation.safety.session import protected_page

CAPABILITY_PATH = Path("evidence/artifacts/member_balances_v1.json")


def main():
    parser = argparse.ArgumentParser()
    parser.add_argument("--member-id", default="67890")
    parser.add_argument("--headless", action="store_true")
    args = parser.parse_args()
    capability = load_capability(CAPABILITY_PATH)
    evidence = RunEvidence("replay")
    with protected_page(headless=args.headless) as page:
        page.goto("http://127.0.0.1:5000")
        controller = None if args.headless else HandoffController()
        result = ReplayExecutor(page, handoff=controller, evidence=evidence).execute(
            capability, {"member_id": args.member_id})
        evidence.record("result", status=result.status.value, step=result.step,
                        outputs_collected=list(result.outputs))
        print(result.model_dump_json(indent=2))
        print(f"Evidence: {evidence.directory}")


if __name__ == "__main__":
    main()
