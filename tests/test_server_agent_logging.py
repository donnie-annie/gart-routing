from pathlib import Path


ROOT = Path(__file__).resolve().parents[1]


def test_server_agent_file_handler_writes_to_project_logs_directory():
    text = (ROOT / "server_agent.py").read_text(encoding="utf-8")

    assert "SERVER_AGENT_LOG_FILE" in text
    assert '"logs"' in text
    assert '"server_agent.log"' in text
    assert 'FileHandler("./server.log"' not in text


def test_start_suite_does_not_redirect_server_agent_stdout_to_file_handler_target():
    text = (ROOT / "start_suite.sh").read_text(encoding="utf-8")

    assert "> logs/server_agent.log" not in text
    assert "> logs/server_agent.stdout.log" in text
