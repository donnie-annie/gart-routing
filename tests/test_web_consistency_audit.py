import importlib.util
from pathlib import Path


ROOT = Path(__file__).resolve().parents[1]
spec = importlib.util.spec_from_file_location(
    "web_consistency_audit",
    ROOT / "tools" / "web_consistency_audit.py",
)
web_consistency_audit = importlib.util.module_from_spec(spec)
spec.loader.exec_module(web_consistency_audit)
audit_payloads = web_consistency_audit.audit_payloads


def test_audit_accepts_route_session_matching_switch_links():
    graph = {
        "nodes": [
            {"id": 31, "data": {"node_type": "switch"}},
            {"id": 28, "data": {"node_type": "switch"}},
            {"id": 6, "data": {"node_type": "switch"}},
        ],
        "edges": [
            {"source": 31, "target": 28, "data": {"edge_type": "switch_link"}},
            {"source": 28, "target": 6, "data": {"edge_type": "switch_link"}},
        ],
    }
    sessions = {"sessions": [{"id": "s1", "switch_path": [31, 28, 6]}]}

    assert audit_payloads(graph, sessions) == []


def test_audit_reports_route_session_missing_switch_link():
    graph = {
        "nodes": [
            {"id": 31, "data": {"node_type": "switch"}},
            {"id": 28, "data": {"node_type": "switch"}},
            {"id": 6, "data": {"node_type": "switch"}},
        ],
        "edges": [
            {"source": 31, "target": 28, "data": {"edge_type": "switch_link"}},
        ],
    }
    sessions = {"sessions": [{"id": "s1", "switch_path": [31, 28, 6]}]}

    errors = audit_payloads(graph, sessions)

    assert "route session s1 missing switch_link 28<->6" in errors
