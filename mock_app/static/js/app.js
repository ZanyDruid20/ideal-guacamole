const resumeButton = document.getElementById("resume-button");
const cancelButton = document.getElementById("cancel-button");

const runStatus = document.getElementById("run-status");
const controlOwner = document.getElementById("control-owner");
const activityLog = document.getElementById("activity-log");


if (resumeButton) {
    resumeButton.addEventListener("click", function () {
        runStatus.textContent = "Running";
        controlOwner.textContent = "Automation";
        activityLog.textContent =
            "Human operator returned control to automation.";
    });
}


if (cancelButton) {
    cancelButton.addEventListener("click", function () {
        runStatus.textContent = "Cancelled";
        controlOwner.textContent = "Human";
        activityLog.textContent =
            "Human operator cancelled the automation run.";
    });
}