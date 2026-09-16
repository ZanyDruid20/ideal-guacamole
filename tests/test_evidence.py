import json
from unittest.mock import Mock

from automation.evidence import RunEvidence


def test_failure_snapshot_and_log_exclude_exception_secrets(tmp_path):
    evidence = RunEvidence("test", root=tmp_path)
    page = Mock()
    page.evaluate.return_value = {"ready_state": "complete", "element_counts": {"input": 1}}
    evidence.failure(page, 2, ValueError("password=do-not-save"))
    files = list(evidence.directory.glob("*.json"))
    assert len(files) == 2
    for file in files:
        assert "do-not-save" not in file.read_text()
    events = json.loads((evidence.directory / "events.json").read_text())
    assert events[-1]["step"] == 2
    assert (evidence.directory / events[-1]["snapshot"]).exists()


def test_snapshot_failure_still_records_original_failure(tmp_path):
    evidence = RunEvidence("test", root=tmp_path)
    page = Mock()
    page.evaluate.side_effect = RuntimeError("closed")
    evidence.failure(page, 1, ValueError("bad state"))
    assert evidence.events[-1]["error_type"] == "ValueError"
    assert evidence.events[-1]["capture_error"] == "RuntimeError"
