from automation.handoff.controller import HandoffController

def test_handoff_control_flow():
    controller = HandoffController()

    # Automation initially owns control
    assert controller.is_human_controlled() is False

    # Automation requests human intervention
    controller.request_handoff(
        reason="Manual verification required",
        step=2,
    )

    assert controller.is_human_controlled() is True
    assert controller.reason == "Manual verification required"
    assert controller.step == 2

    # Human finishes and returns control
    controller.resume_automation()

    assert controller.is_human_controlled() is False