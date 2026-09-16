# Project review checklist

Work through these sections in order. Check a box after reviewing it, even if you find a problem; record the problem in the comments. This is a review worksheet, not a claim that the checks have passed.

For each comment, include the file and line, what you observed, the expected behavior, and any follow-up needed. Use `Question`, `Fix`, or `README note` to label your comments.

## 1. Understand the project and entry points

Review: [run_discovery.py](run_discovery.py), [run_replay.py](run_replay.py), [run_handoff_demo.py](run_handoff_demo.py).

- [ ] Explain what each script does in your own words.
- [ ] Trace discovery → compiled capability → saved JSON → deterministic replay.
- [ ] Identify the server URL, member IDs, goal, and artifact paths each script uses.
- [ ] Check that success, business outcome, and failure produce accurate messages and log filenames.
- [ ] Check that the browser closes when an exception occurs.
- [ ] Record which scripts need an API key and which can run without an LLM call.

**Comments / README notes:**

> Write here.

## 2. Mock application — `mock_app/`

Review: [app.py](mock_app/app.py), `templates/`, `static/css/`, `static/js/`, and `data/members.json`.

- [ ] Follow the `/`, `/search`, and `/operator` routes through their templates.
- [ ] Try a known member, an unknown member, and an empty search.
- [ ] Compare displayed checking and savings balances against the sample data.
- [ ] Check that input labels, button names, and account-table markup match the automation locators.
- [ ] Confirm the sample data is appropriate to share and explain that this is a local mock application.
- [ ] Record how to start the server and its expected URL.

**Comments / README notes:**

> Write here.

## 3. Discovery — `automation/discovery/`

Review: [agent.py](automation/discovery/agent.py) and [prompts.py](automation/discovery/prompts.py).

- [ ] Explain what `observe_page()` collects and what is sent to the model.
- [ ] Check that the prompt's action format matches `execute_action()`.
- [ ] Verify that observed row IDs map to the same rows during extraction.
- [ ] Review invalid JSON, unsupported actions, missing targets, and missing output names.
- [ ] Check the stopping conditions: `done`, errors, and maximum steps.
- [ ] Review whether declaring `done` actually proves the requested outputs were collected.
- [ ] Check whether observations and console output expose member details or other sensitive values.
- [ ] Record the configured model and environment-variable requirements from the code.

**Comments / README notes:**

> Write here.

## 4. Capability definitions — `automation/capability/`

Review: [schema.py](automation/capability/schema.py), [compiler.py](automation/capability/compiler.py), and [serializer.py](automation/capability/serializer.py).

- [ ] Understand actions, targets, inputs, outputs, checkpoints, risk levels, and result statuses.
- [ ] Check validation for missing action values, targets, checkpoints, and undeclared outputs.
- [ ] Identify which compiler behavior is specific to the member-balance application.
- [ ] Verify that compilation substitutes `{{member_id}}` rather than storing a fixed member ID.
- [ ] Check unsupported discovery actions and unsuccessful or incomplete discovery results.
- [ ] Check that extracted balances use the intended account rows and columns.
- [ ] Confirm that saving and loading preserves the capability and rejects malformed JSON.
- [ ] Review whether retry and risk fields are implemented by execution or only defined in the schema.

**Comments / README notes:**

> Write here.

## 5. Replay — `automation/replay/`

Review: [executor.py](automation/replay/executor.py).

- [ ] Follow TYPE, CLICK, EXTRACT, NAVIGATE, and WAIT through execution.
- [ ] Check input substitution, missing inputs, and output collection.
- [ ] Verify attached checkpoints and the final success condition run at the intended times.
- [ ] Check successful lookup, `Member not found`, missing elements, and failed checkpoints.
- [ ] Confirm failures identify the failing step and preserve outputs already collected.
- [ ] Check that the executor supports the target types accepted by the schema.
- [ ] Check whether safety validation and human handoff are connected to replay.
- [ ] Review the package filename `___init__.py`: it currently has three leading underscores rather than the usual two.

**Comments / README notes:**

> Write here.

## 6. Safety — `automation/safety/`

Review: [guardrails.py](automation/safety/guardrails.py).

- [ ] Check safe, risky, and irreversible action handling.
- [ ] Locate actual calls to `validate_action()` and `validate_url()` in execution paths.
- [ ] Test allowed URLs, external URLs, and URLs that merely start with the allowed URL text.
- [ ] Check redaction inside nested dictionaries and lists.
- [ ] Review sensitive values embedded in free-text goals, URLs, console output, and screenshots; key-based redaction alone does not cover these.
- [ ] Distinguish implemented enforcement from future safety plans in the README.

**Comments / README notes:**

> Write here.

## 7. Human handoff — `automation/handoff/`

Review: [controller.py](automation/handoff/controller.py) and [run_handoff_demo.py](run_handoff_demo.py).

- [ ] Follow request → human control → resume and check the recorded reason and step.
- [ ] Verify automation pauses while the person uses the existing browser session.
- [ ] Check that the state after manual interaction is verified before claiming success.
- [ ] Review whether the log's `session_preserved` claim is supported by the verification result.
- [ ] Distinguish the standalone handoff demo from integration with the replay executor.

**Comments / README notes:**

> Write here.

## 8. Evidence — `automation/evidence.py` and `evidence/`

Review: [evidence.py](automation/evidence.py), `evidence/artifacts/`, `evidence/logs/`, and `evidence/screenshots/`.

- [ ] Check directory creation, JSON writing, timestamps, and full-page screenshots.
- [ ] Open the saved capability and compare it with the compiler's expected output.
- [ ] Match each log and screenshot to the run and outcome it demonstrates.
- [ ] Confirm success filenames do not hide failed runs.
- [ ] Check whether repeated runs overwrite evidence and decide whether that is acceptable.
- [ ] Review logs and screenshots before sharing them.
- [ ] Record which evidence demonstrates discovery, replay, business outcome, and handoff.

**Comments / README notes:**

> Write here.

## 9. Tests — `tests/`

Review: `test_schema.py`, `test_serializer.py`, `test_guardrails.py`, `test_handoff.py`, and `test_replay.py`.

- [ ] Map each existing test to the behavior it verifies.
- [ ] Run the suite and record the actual result; distinguish code failures from environment/setup failures.
- [ ] Add replay coverage: `tests/test_replay.py` is currently empty.
- [ ] Identify missing compiler, discovery, evidence-writing, and mock-application tests.
- [ ] Cover both successful execution and failure/business-outcome paths.
- [ ] Separate tests using mocks from checks using a real browser or live model.
- [ ] Record any manual checks that are not covered by automated tests.

Run from the repository root with the virtual environment active:

```powershell
python -m pytest tests -v
```

**Test result / date / comments:**

> Write here. Tests were not run as part of creating this checklist.

## 10. Root configuration and repository housekeeping

Review: [requirements.txt](requirements.txt), [pytest.ini](pytest.ini), [.gitignore](.gitignore), [README.md](README.md), and [REPORT.md](REPORT.md).

- [ ] Check dependency installation in a clean virtual environment.
- [ ] Document the Python version actually tested and the browser-installation step.
- [ ] Check that pytest can import `automation` from the repository root.
- [ ] Review `.gitignore`: it currently only lists `.env`; consider the virtual environment, bytecode, pytest cache, and temporary files.
- [ ] Decide which generated evidence belongs in version control.
- [ ] Provide configuration examples with placeholders, never actual API keys.
- [ ] Decide what belongs in the README versus the report; the README currently contains only a title and the report is empty.

**Comments / README notes:**

> Write here.

## 11. Write the README from your review notes

Use this as your README outline. Describe only behavior you verified.

- [ ] **Purpose:** what the project demonstrates and the member-balance workflow.
- [ ] **How it works:** discovery, compilation, saved capabilities, replay, and human handoff.
- [ ] **Folder guide:** a short explanation of `automation/`, `mock_app/`, `tests/`, and `evidence/`.
- [ ] **Prerequisites:** tested Python version, virtual environment, dependencies, browser installation, and configuration.
- [ ] **Setup:** exact commands verified from a clean checkout.
- [ ] **Run the mock app:** server command and URL; explain that it stays running in a separate terminal.
- [ ] **Run discovery:** command, required configuration, expected output, and saved artifact.
- [ ] **Run replay:** command, prerequisite capability file, input selection, and expected statuses.
- [ ] **Run handoff:** command and the manual steps the person must complete.
- [ ] **Run tests:** command, coverage summary, and any manual checks still needed.
- [ ] **Evidence:** where logs and screenshots are saved and what each demonstrates.
- [ ] **Limitations:** application-specific selectors, failure handling, safety integration, and other gaps found during review.
- [ ] **Troubleshooting:** import errors, missing browser installation, server availability, and configuration problems you reproduced.
- [ ] **Next steps:** prioritize remaining work from your comments.

Commands to verify before including them in the README:

```powershell
python -m venv venv
.\venv\Scripts\Activate.ps1
python -m pip install -r requirements.txt
python -m playwright install chromium
python mock_app/app.py
```

With the server running, use a second terminal with the virtual environment active:

```powershell
python run_discovery.py
python run_replay.py
python run_handoff_demo.py
python -m pytest tests -v
```

**README draft notes:**

> Write here.

## Review follow-ups

| Priority | File / line | Finding or question | Planned change | Status |
| --- | --- | --- | --- | --- |
| | | | | |
| | | | | |
| | | | | |
