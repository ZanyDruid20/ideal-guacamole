from unittest.mock import Mock

import pytest
from playwright.sync_api import TimeoutError

from automation.capability.schema import RetryPolicy
from automation.replay.executor import ReplayExecutor


def test_safe_timeout_retries_then_succeeds():
    page = Mock(url="http://127.0.0.1:5000")
    evidence = Mock()
    executor = ReplayExecutor(page, evidence=evidence)
    operation = Mock(side_effect=[TimeoutError("slow"), "balance"])
    assert executor._retry(operation, RetryPolicy(max_attempts=2, delay_ms=10), 1) == "balance"
    assert operation.call_count == 2
    page.wait_for_timeout.assert_called_once_with(10)
    evidence.record.assert_called_once_with("recoverable_failure", step=1, attempt=1, reason="read_or_wait_timeout")


def test_retry_budget_is_bounded():
    operation = Mock(side_effect=TimeoutError("slow"))
    executor = ReplayExecutor(Mock(url="http://127.0.0.1:5000"))
    with pytest.raises(TimeoutError):
        executor._retry(operation, RetryPolicy(max_attempts=3), 1)
    assert operation.call_count == 3


def test_non_transient_errors_are_not_retried():
    operation = Mock(side_effect=ValueError("invalid"))
    with pytest.raises(ValueError):
        ReplayExecutor(Mock())._retry(operation, RetryPolicy(max_attempts=3), 1)
    assert operation.call_count == 1


@pytest.mark.parametrize("attempts", [0, 4, -1])
def test_invalid_retry_budget_is_rejected(attempts):
    with pytest.raises(ValueError):
        RetryPolicy(max_attempts=attempts)
