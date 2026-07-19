from pathlib import Path


ROOT = Path(__file__).resolve().parents[1]
WEB_UI = ROOT / "web_ui_html.py"


def test_web_ui_uses_slim_graph_refresh_and_inflight_guard():
    text = WEB_UI.read_text(encoding="utf-8")

    assert "let isRefreshInFlight = false;" in text
    assert "fetch('/api/graph?include_flows=0')" in text
    assert "computeGraphSignature(data)" in text


def test_web_ui_loads_switch_flows_on_demand():
    text = WEB_UI.read_text(encoding="utf-8")

    assert "async function loadSwitchFlowsForSidebar" in text
    assert "fetch('/api/switch/' + encodeURIComponent(String(switchId)) + '/flows')" in text
