# Bank Member Automation Agent

## Test failure-triggered replay handoff

Keep the mock app running in one terminal:

```powershell
python mock_app/app.py
```

In another terminal with the virtual environment active:

```powershell
python run_replay_handoff.py
```

This controlled demo uses an in-memory copy of the saved capability. It requires
the Accounts checkpoint before extraction, while starting on the search page,
so the checkpoint deliberately fails. When automation pauses, search for member
`12345` in the same open browser. Type `resume` in the terminal and describe your
manual change without including member details or secrets. The checkpoint must
pass before balance extraction continues. Trying `resume` before fixing the page
keeps automation paused. Type `abort` to stop instead.

Each demo writes `evidence/logs/replay_handoff_<run-id>.json`, including handoff
events, the operator's note, the final status, and collected output names.
Operator notes are free text: review them before sharing evidence.

Normal replay also enables checkpoint handoff. It can continue after a completed
action's checkpoint failure, a WAIT failure, or a final checkpoint failure.
It does not repeat failed clicks, bypass policy violations, or automatically
recover arbitrary action errors. Discovery handoff remains separate work.

This project demonstrates browser automation against a mock member account application.

A model agent discovers the steps needed to retrieve checking and savings balances. Those steps are compiled into a reusable JSON capability, which can then be replayed without an LLM being called

## Requirements
- Python 3.14 (used during development)
- Git
- OpenAI API key and network access for live discovery
- Playwright Chromium, installed during setup

Run all commands from the repository root. The examples below use Windows PowerShell.


## Setup

Clone this repository and open its folder:

```powershell
git clone https://github.com/ZanyDruid20/ideal-guacamole.git
cd ideal-guacamole
```

Create and activate a virtual environment:

```powershell
python -m venv venv
.\venv\Scripts\Activate.ps1
```

Install dependencies and the browser:

```powershell
python -m pip install -r requirements.txt
python -m playwright install chromium
```

For live discovery, create a `.env` file in the repository root:

```dotenv
OPENAI_API_KEY=your_api_key_here
```

Do not commit this file. The discovery model is configured in
`automation/discovery/agent.py`; the API account must have access to
that model.


## Start the mock application

In the first terminal, activate the virtual environment and run:

```powershell
python mock_app/app.py
```

Keep this terminal running. The application is available at:

http://127.0.0.1:5000

The browser scripts expect this address.

## Demo: discover a workflow, then replay it

Open a second terminal in the repository root and activate the environment:

```powershell
.\venv\Scripts\Activate.ps1
```

### 1. Run the agent on a goal

```powershell
python run_discovery.py
```

The goal is defined by `GOAL` in `run_discovery.py`:

> Find member 12345 and return their checking and savings balances.

The agent observes the page, chooses one action at a time, executes it, and records the actions and extracted outputs.

After successful discovery, the script compiles and saves the capability:

```text
evidence/artifacts/member_balances_v1.json
```

The discovery log is written to:

```text
evidence/logs/discovery_success.json
```

Check the recorded status to confirm the run succeeded.

### 2. Replay the resulting artifact

```powershell
python run_replay.py
```

This script loads `evidence/artifacts/member_balances_v1.json` and runs
its saved instructions without asking the model to choose actions.

The member ID is supplied in the `inputs` dictionary in `run_replay.py`.
Change that value to replay the workflow for a different member in the
mock dataset.

The script prints an execution result containing a status and any
collected outputs. Possible outcomes include:

- `success`: actions and the final checkpoint passed.
- `business_outcome`: the application reported “Member not found.”
- `hard_failure`: an action or checkpoint failed.

Replay logs and screenshots are stored under `evidence/`.

## Run without live model services

After installing dependencies and Chromium, replay can run without an
API key or model calls by using the example capability included in
`evidence/artifacts/`.

Start the local mock application, then run:

```powershell
python run_replay.py
```

Replay still requires the local application and browser. Live discovery requires access to the configured model service.

## Run tests

```powershell
python -m pytest tests -v
```

To run only the replay tests:

```powershell
python -m pytest tests/test_replay.py -v
```

The replay tests use mocked browser objects, so they do not require a
running Flask application, browser session, or model service.

## Human handoff demonstration

With the mock application running:

```powershell
python run_handoff_demo.py
```

Follow the terminal instructions to interact manually with the open
browser, then return control to the script.

This older demo shows manual control transfer. Use `python run_replay_handoff.py`
for the integrated checkpoint-failure, verification, and resume demonstration.

## Project structure

- `automation/discovery/`: page observation and model-driven actions.
- `automation/capability/`: schema, compilation, and JSON serialization.
- `automation/replay/`: execution of saved capabilities.
- `automation/handoff/`: human-control state tracking.
- `automation/safety/`: guardrail and redaction helpers.
- `automation/evidence.py`: log and screenshot helpers.
- `mock_app/`: local Flask application and sample member data.
- `tests/`: automated tests.
- `evidence/`: saved capabilities, logs, and screenshots.
- `REPORT.md`: design decisions, trade-offs, and limitations.

## Current limitations

The compiler is specific to the mock member-balance application and
uses application-specific labels and selectors. Changes to the UI may cause replay to fail.

Replay retries only read-only EXTRACT and WAIT timeouts when the artifact specifies a retry policy (at most three attempts). Clicks are never automatically repeated. Checkpoint failures can request handoff; policy violations and unsafe-to-resume action errors stop. Discovery enforces action policy and a step budget but does not resume through handoff. Automatic UI repair and desktop automation are not implemented.

## Verification and evidence

Run all unit tests with `python -m pytest tests -v`.
For a headless browser verification requiring no model or separately started server:

```powershell
python verify_system.py
```

This starts temporary local servers and checks success, not-found, an external
redirect (the forbidden server must receive zero requests), bounded recovery,
same-page handoff, and abort. Its operator is automated and labeled as such;
it is not evidence of a live LLM discovery run. The earlier genuine discovery
summary remains in `evidence/logs/discovery_success.json`.

New runs write timestamped events under `evidence/runs/<type>_<id>/`.
On replay failure they save a structural DOM summary (element counts and document
readiness), excluding page text, attributes, URLs, and input values. This is less
visually detailed than a screenshot but avoids saving private page contents.
Existing `evidence/logs/` and screenshots are historical synthetic-demo evidence.

```powershell
python run_replay.py --member-id 67890
python run_replay.py --member-id unknown --headless
```

The first example retrieves balances; the second produces a business outcome.
Headless replay disables interactive handoff. Browser runners enforce an origin allowlist on HTTP requests, redirect destinations, and popup requests; service workers and WebSockets are blocked. This is a local trusted-app prototype, not an OS security sandbox. Use synthetic data only. Discovery sends page observations to the model; do not use it with production credentials or customer information.
