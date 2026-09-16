class HandoffController:
    def __init__(self):
        self.active = False
        self.reason = None
        self.step = None

    def request_handoff(self, reason, step):
        self.active = True
        self.reason = reason
        self.step = step

    def resume_automation(self):
        self.active = False

    def is_human_controlled(self):
        return self.active
