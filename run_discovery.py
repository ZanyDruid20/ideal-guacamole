from pathlib import Path

from automation.capability.serializer import save_capability
from automation.discovery.agent import run_discovery
from automation.capability.compiler import compile_member_balance_capability
from automation.evidence import save_log
from automation.evidence import RunEvidence
from automation.safety.session import protected_page


GOAL = "Find member 12345 and return their checking and savings balances."


def main():
    evidence = RunEvidence("discovery")
    with protected_page() as page:
        page.goto("http://127.0.0.1:5000")

        result = run_discovery(page=page, goal=GOAL, evidence=evidence)
        evidence.record("result", status=result["status"], outputs_collected=list(result["outputs"]))
        save_log(
            "discovery_success.json",
            {
                "run_type": "llm_discovery",
                "goal": "Find a member and return their checking and savings balances.",
                "member_id": "12345",
                "status": result["status"],
                "actions": [
                    action["action"]
                    for action in result["actions"]
                ],
                "outputs_collected": list(
                    result.get("outputs", {}).keys()
                ),
            }
        )
        print("\nDiscovery result:")
        print(result["status"])
        if result["status"] == "success":
            capability = compile_member_balance_capability(result)
            save_capability(capability, Path("evidence/artifacts/member_balances_v1.json"))
            print("\nCapability saved:")
            print(capability.model_dump_json(indent=2))

        print(f"Detailed evidence: {evidence.directory}")


if __name__ == "__main__":
    main()
