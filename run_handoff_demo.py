from playwright.sync_api import sync_playwright
from automation.evidence import save_log, save_screenshot
from automation.handoff.controller import HandoffController


def main():
    controller = HandoffController()

    with sync_playwright() as playwright:
        browser = playwright.chromium.launch(headless=False)
        page = browser.new_page()

        # Automation starts the session
        page.goto("http://127.0.0.1:5000")

        print("Automation has control.")

        # Automation reaches a point where human help is needed
        controller.request_handoff(
            reason="Manual verification required",
            step=2,
        )

        print("\nHANDOFF REQUESTED")
        print(f"Reason: {controller.reason}")
        print(f"Step: {controller.step}")
        print(f"Current URL: {page.url}")

        # Automation pauses while the human controls
        if controller.is_human_controlled():
            input(
                "\nUse the OPEN BROWSER manually. "
                "Search for member 12345, then press ENTER here..."
            )
        save_screenshot(page, "handoff.png")
        save_log(
            "handoff.json",
            {
                "run_type": "human_handoff",
                "reason": controller.reason,
                "step": controller.step,
                "current_url": page.url,
                "human_action": (
                    "Human manually completed the requested "
                    "interaction in the same live browser session."

                ),
                "session_preserved": True,
            }
        )
        # Human returns control
        controller.resume_automation()

        print("\nAutomation resumed.")
        print(f"Current URL: {page.url}")

        # Verify we're still in the SAME live session
        body_text = page.locator("body").inner_text()

        if "Jonathan Carter" in body_text:
            print("Same-session handoff verified.")
        else:
            print("Handoff verification failed.")

        input("\nPress ENTER to close the browser...")
        browser.close()


if __name__ == "__main__":
    main()
