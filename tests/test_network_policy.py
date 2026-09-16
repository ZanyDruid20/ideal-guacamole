from unittest.mock import Mock

from automation.safety.guardrails import Guardrails


def test_redirect_is_checked_without_following_it():
    context = Mock()
    with Guardrails().protect_context(context):
        handler = context.route.call_args.args[1]
        route = Mock()
        route.request.url = "http://127.0.0.1:5000/redirect"
        route.fetch.return_value.status = 302
        route.fetch.return_value.headers = {"location": "https://outside.example"}
        handler(route)
        route.fetch.assert_called_once_with(max_redirects=0)
        route.abort.assert_called_once_with("blockedbyclient")
        route.fulfill.assert_not_called()


def test_external_request_is_not_fetched():
    context = Mock()
    with Guardrails().protect_context(context):
        route = Mock()
        route.request.url = "https://outside.example"
        context.route.call_args.args[1](route)
        route.fetch.assert_not_called()
        route.abort.assert_called_once()
