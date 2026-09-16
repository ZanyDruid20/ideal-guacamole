from contextlib import contextmanager
from playwright.sync_api import sync_playwright
from .guardrails import Guardrails


@contextmanager
def protected_page(policy=None, headless=False):
    policy = policy if policy is not None else Guardrails()
    with sync_playwright() as playwright:
        browser = playwright.chromium.launch(headless=headless)
        try:
            context = browser.new_context(service_workers="block", accept_downloads=False)
            with policy.protect_context(context):
                page = context.new_page()
                page.set_default_timeout(3000)
                yield page
        finally:
            browser.close()
