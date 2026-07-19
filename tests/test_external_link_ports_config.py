import importlib


def test_external_link_ports_parses_dpid_port_pairs(monkeypatch):
    monkeypatch.setenv("EXTERNAL_LINK_PORTS", "1:20, 42:7")

    import common_config
    importlib.reload(common_config)

    assert common_config.EXTERNAL_LINK_PORTS == {1: {20}, 42: {7}}


def test_controller_applies_external_link_port_whitelist():
    from pathlib import Path

    text = (Path(__file__).resolve().parents[1] / "controller.py").read_text(encoding="utf-8")

    assert "EXTERNAL_LINK_PORTS" in text
    assert "_apply_configured_external_link_ports" in text
