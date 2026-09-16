import json
import os

from dotenv import load_dotenv
from openai import OpenAI
from playwright.sync_api import Page

from .prompts import DISCOVERY_SYSTEM_PROMPT

# Load environment configuration and create the model client.

load_dotenv()
client = OpenAI(
    api_key=os.getenv("OPENAI_API_KEY")
)

# Collect page text and element details so the model can choose its next action.
def observe_page(page: Page) -> dict:
    observation = {
        "url": page.url,
        "text": page.inner_text("body"),
        "inputs": [],
        "buttons": [],
        "rows": [],
    }

    # Observe inputs
    inputs = page.locator("input")
    # Assign each table row a positional ID that extraction can resolve.
    for i in range(inputs.count()):
        input_element = inputs.nth(i)

        input_id = input_element.get_attribute("id")
        input_type = input_element.get_attribute("type")
        input_name = input_element.get_attribute("name")
        placeholder = input_element.get_attribute("placeholder")
        input_value = input_element.input_value()

        label = None

        if input_id:
            label_element = page.locator(f'label[for="{input_id}"]')

            if label_element.count() > 0:
                label = label_element.first.inner_text()

        observation["inputs"].append({
            "type": input_type,
            "name": input_name,
            "id": input_id,
            "placeholder": placeholder,
            "label": label,
            "value": input_value,
        })

    # Observe buttons
    buttons = page.locator("button")

    for i in range(buttons.count()):
        button = buttons.nth(i)

        observation["buttons"].append({
            "name": button.inner_text(),
            "id": button.get_attribute("id"),
        })

    rows = page.locator("tbody tr")

    for i in range(rows.count()):
        row = rows.nth(i)

        observation["rows"].append({
            "id": f"row_{i}",
            "text": row.inner_text(),
        })

    return observation

# Ask the model for one next action using the goal, page state, and collected outputs.
def decide_next_action(goal: str, observation: dict, outputs: dict) -> dict:
    user_message = f"""
Goal:
{goal}

Current application state:
{json.dumps(observation, indent=2)}

Outputs already collected:
{json.dumps(outputs, indent=2)}

Choose the single next action needed to make progress toward the goal.

Return only valid JSON.
"""

    response = client.responses.create(
        model="gpt-5.6-luna",
        instructions=DISCOVERY_SYSTEM_PROMPT,
        input=user_message,
    )

    return json.loads(response.output_text)

# Translate the selected action into a Playwright browser operation.
# Validate the observed row ID and return that row's text.
def execute_action(page: Page, action: dict) -> str | None:
    action_type = action.get("action")
    target = action.get("target", {})
    value = action.get("value")

    if action_type == "type":
        label = target.get("label")

        if label:
            page.get_by_label(label).fill(value)
        else:
            raise ValueError("TYPE action requires a target label")

    elif action_type == "click":
        name = target.get("name")

        if name:
            page.get_by_role("button", name=name).click()
        else:
            raise ValueError("CLICK action requires a target name")

    elif action_type == "extract":
        row_id = target.get("id")

        if not row_id:
            raise ValueError(
                "EXTRACT action requires an observed row id"
            )

        if not row_id.startswith("row_"):
            raise ValueError(
                f"Invalid row id: {row_id}"
            )

        try:
            row_index = int(row_id.split("_", 1)[1])
        except ValueError:
            raise ValueError(
                f"Invalid row id: {row_id}"
            )

        rows = page.locator("tbody tr")

        if row_index < 0 or row_index >= rows.count():
            raise ValueError(
                f"Row does not exist: {row_id}"
            )

        return rows.nth(row_index).inner_text()

    elif action_type == "navigate":
        if value:
            page.goto(value)
        else:
            raise ValueError(
                "NAVIGATE action requires a URL"
            )

    elif action_type == "wait":
        selector = target.get("selector")

        if selector:
            page.locator(selector).wait_for()
        else:
            page.wait_for_timeout(1000)

    elif action_type == "done":
        return None

    else:
        raise ValueError(
            f"Unknown action type: {action_type}"
        )

    return None


def run_discovery(
    page: Page,
    goal: str,
    max_steps: int = 15
) -> dict:
    recorded_actions = []
    outputs = {}

    for step in range(max_steps):

        # 1. Observe current application state
        observation = observe_page(page)

        print(f"\nObservation {step + 1}:")
        print(json.dumps(observation, indent=2))

        # 2. Ask LLM for exactly one next action
        action = decide_next_action(
            goal,
            observation,
            outputs
        )

        print(f"Step {step + 1}: {action}")

        # 3. Stop when goal is complete
        if action.get("action") == "done":
            return {
                "status": "success",
                "actions": recorded_actions,
                "outputs": outputs,
            }

        # 4. Execute action using Playwright
        result = execute_action(
            page,
            action
        )

        # 5. Save extracted values
        if action.get("action") == "extract":
            save_as = action.get("save_as")

            if not save_as:
                raise ValueError(
                    "EXTRACT action requires save_as"
                )

            outputs[save_as] = result

        # 6. Record successful action
        recorded_actions.append(action)

    # Prevent infinite discovery loops
    return {
        "status": "max_steps_reached",
        "actions": recorded_actions,
        "outputs": outputs,
    }