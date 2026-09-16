from pathlib import Path

from playwright.sync_api import sync_playwright

from automation.capability.serializer import load_capability
from automation.replay.executor import ReplayExecutor
from automation.evidence import save_log


CAPABILITY_PATH = Path(
    "evidence/artifacts/member_balances_v1.json"
)


def main():
    capability = load_capability(CAPABILITY_PATH)

    with sync_playwright() as playwright:
        browser = playwright.chromium.launch(headless=False)

        page = browser.new_page()
        page.goto("http://127.0.0.1:5000")

        executor = ReplayExecutor(page)

        result = executor.execute(
            capability=capability,
            inputs={
                "member_id": "67890"
            }
        )
        save_log(
            "replay_success.json",
        {
            "run_type": "deterministic_replay",
            "capability": capability.name,
            "version": capability.version,
            "inputs": {
                "member_id": "67890"
            },
            "result": result.model_dump(),
        }
    )

        print("\nReplay result:")
        print(result.model_dump_json(indent=2))

        browser.close()


if __name__ == "__main__":
    main()