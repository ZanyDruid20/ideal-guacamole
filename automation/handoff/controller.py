class HandoffController:
    def __init__(self):
        self.active = False
        self.reason = None
        self.step = None
        self.events = []

    def request_handoff(self, reason, step):
        self.active = True
        self.reason = reason
        self.step = step

    def resume_automation(self):
        self.active = False

    def is_human_controlled(self):
        return self.active

    def intervene(self, *, page, capability, step, reason, verify, read_input=None):
        """Keep automation paused until verification succeeds or the operator aborts."""
        read_input = read_input or input
        self.request_handoff(reason, step)
        self.events.append({"event": "requested", "capability": capability, "step": step})
        print(f"\nHandoff requested: {capability}, step {step}")
        print(reason)
        print("Use the SAME open browser to correct the page. Automation is paused.")
        while self.active:
            try:
                choice = read_input("Type resume to verify, or abort: ").strip().lower()
            except (EOFError, KeyboardInterrupt):
                choice = "abort"
            if choice == "abort":
                self.active = False
                self.events.append({"event": "aborted", "step": step})
                return False
            if choice != "resume":
                continue
            try:
                note = read_input("Describe your manual change (no member details or secrets): ").strip()
            except (EOFError, KeyboardInterrupt):
                self.active = False
                self.events.append({"event": "aborted", "step": step})
                return False
            if not note:
                print("Please describe the change before resuming.")
                continue
            try:
                verify()
            except Exception as error:
                self.events.append({"event": "verification_failed", "step": step})
                print(f"Verification failed ({type(error).__name__}); automation remains paused.")
                continue
            self.events.append({"event": "resumed", "step": step, "operator_note": note})
            self.resume_automation()
            print("Checkpoint passed. Automation resumed in the same browser.")
            return True
