# Bank Member Automation Agent
This prohect demonstrates browser automation against a mock member account application.

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

Install dependiencies and the browser:

```powershell
python -m pip install -r requirements.txt
python -m playwright install chromium
```

For live discovery, create a `.env ` file in the repository root:

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

This is a separate handoff demonstration; automatic handoff from replay
failures is not currently implemented.

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

Replay reports action and checkpoint failures but does not automatically repair workflows, retry actions, or request human handoff. Guardrail helpers are defined separately and are not currently enforced by the replay executor.