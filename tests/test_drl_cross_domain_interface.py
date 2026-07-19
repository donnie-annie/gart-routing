from pathlib import Path


ROOT = Path(__file__).resolve().parents[1]


def _function_body(text, name):
    marker = f"def {name}"
    start = text.index(marker)
    next_def = text.find("\n    def ", start + len(marker))
    return text[start:] if next_def == -1 else text[start:next_def]


def test_remote_host_updates_do_not_pollute_local_host_table():
    text = (ROOT / "controller.py").read_text(encoding="utf-8")
    init_body = _function_body(text, "__init__")
    handler_body = _function_body(text, "_handle_remote_host_update")

    assert "self.remote_hosts = {}" in init_body
    assert "self.remote_hosts[ip]" in handler_body
    assert "self.host_to_sw_port.setdefault" not in handler_body
    assert "remote host learned" in handler_body


def test_cross_domain_ip_packets_request_root_path_when_destination_not_local():
    text = (ROOT / "packetin_ip.py").read_text(encoding="utf-8")

    assert "[PathRequest] dst_not_local" in text
    assert "app._request_path(" in text
    assert "app.get_path(src_switch_id, dst_switch_id)" in text


def test_drl_request_boundaries_are_logged():
    server_text = (ROOT / "server_agent.py").read_text(encoding="utf-8")
    path_service_text = (ROOT / "gart" / "path_service.py").read_text(encoding="utf-8")
    controller_text = (ROOT / "controller.py").read_text(encoding="utf-8")

    assert "[PathRequest] send_to_root" in controller_text
    assert "[DRL] request_path route_mode=%s" in server_text
    assert "[DRL] path_service response decision_source=%s model_used=%s" in server_text
    assert "route_mode = request.get(\"route_mode\"" in path_service_text
    assert "[请求] route_mode=%s candidates=%d" in path_service_text
