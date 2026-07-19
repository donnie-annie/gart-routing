"""Shared controller, server, routing, and traffic-class configuration."""

import os


def _parse_external_link_ports(raw_value):
    ports = {}
    for item in (raw_value or "").split(","):
        item = item.strip()
        if not item:
            continue
        dpid_text, sep, port_text = item.partition(":")
        if not sep:
            continue
        try:
            dpid = int(dpid_text, 0)
            port = int(port_text, 0)
        except ValueError:
            continue
        ports.setdefault(dpid, set()).add(port)
    return ports

SERVER_CONFIG = {
    'server_ip': os.environ.get('SERVER_AGENT_IP', '127.0.0.1'),
    'server_port': int(os.environ.get('SERVER_AGENT_PORT', '6001')),
    'reconnect_interval': 5
}

CONTROLLER_IP = os.environ.get('SERVER_AGENT_BIND_IP', '0.0.0.0')
CONTROLLER_PORT = int(os.environ.get('SERVER_AGENT_PORT', '6001'))
WEB_PORT = int(os.environ.get('WEB_PORT', '6009'))
PATH_SERVICE_HOST = os.environ.get('PATH_SERVICE_HOST', '127.0.0.1')
PATH_SERVICE_PORT = int(os.environ.get('PATH_SERVICE_PORT', '8889'))

DRL_ROUTE_MODE = os.environ.get("DRL_ROUTE_MODE", "shadow").strip().lower()
if DRL_ROUTE_MODE not in {"spf", "shadow", "hybrid", "drl"}:
    DRL_ROUTE_MODE = "shadow"

DRL_K_CANDIDATES = int(os.environ.get("DRL_K_CANDIDATES", "5"))
DRL_INFERENCE_TIMEOUT_MS = int(os.environ.get("DRL_INFERENCE_TIMEOUT_MS", "100"))
DRL_MIN_CONFIDENCE = float(os.environ.get("DRL_MIN_CONFIDENCE", "0.50"))

# GART Table II flow classes. Existing task labels are mapped to deadline-aware
# flow requirements before requests are sent to the decentralized path service.
GART_FLOW_PROFILES = {
    'task_0': {'flow_type': 'EU', 'deadline_ms': 20.0, 'proportion': 0.05},
    'task_a': {'flow_type': 'EU', 'deadline_ms': 20.0, 'proportion': 0.05},
    'task_1': {'flow_type': 'MU', 'deadline_ms': 50.0, 'proportion': 0.15},
    'task_b': {'flow_type': 'MU', 'deadline_ms': 50.0, 'proportion': 0.15},
    'task_2': {'flow_type': 'LU', 'deadline_ms': 100.0, 'proportion': 0.70},
    'task_c': {'flow_type': 'RT', 'deadline_ms': 200.0, 'proportion': 0.10},
    'default': {'flow_type': 'RT', 'deadline_ms': 200.0, 'proportion': 0.10},
}


def get_gart_flow_profile(task_type):
    return dict(GART_FLOW_PROFILES.get(task_type, GART_FLOW_PROFILES['default']))

# Automatic routes stay warm between short validation runs but remain configurable.
ROUTE_FLOW_IDLE_TIMEOUT = int(os.environ.get("ROUTE_FLOW_IDLE_TIMEOUT", "120"))
ROUTE_FLOW_HARD_TIMEOUT = int(os.environ.get("ROUTE_FLOW_HARD_TIMEOUT", "0"))
FLOW_INSTALL_BARRIER_TIMEOUT = float(os.environ.get("FLOW_INSTALL_BARRIER_TIMEOUT", "0.5"))

# Comma-separated OpenFlow port whitelist for physical/real-network attachments.
# Example: EXTERNAL_LINK_PORTS=1:20 marks s1:port20 as a link/external port before LLDP learns it.
EXTERNAL_LINK_PORTS = _parse_external_link_ports(os.environ.get("EXTERNAL_LINK_PORTS", ""))
EXTERNAL_ARP_ALLOWED_PREFIXES = [
    item.strip()
    for item in os.environ.get("EXTERNAL_ARP_ALLOWED_PREFIXES", "10.0.0.0/24").split(",")
    if item.strip()
]
VIRTUAL_SWITCH_DPID_MAX = int(os.environ.get("VIRTUAL_SWITCH_DPID_MAX", "1000"))
HYBRID_GATEWAY_IP = os.environ.get("HYBRID_GATEWAY_IP", "10.0.0.254")
HYBRID_GATEWAY_MAC = os.environ.get("HYBRID_GATEWAY_MAC", "02:00:00:00:fe:01")
HYBRID_REAL_ROUTES = os.environ.get("HYBRID_REAL_ROUTES", "192.168.103.0/24")

HOST_PORT_TASK_RANGES = [
    (1, 5000, 'task_0'),
    (5001, 10000, 'task_1'),
    (10001, 65535, 'task_2'),
]

TASK_POLICY_MAP = {
    'task_0': 'shortest_path',
    'task_1': 'shortest_path',
    'task_2': 'shortest_path',
    'task_a': 'shortest_path',
    'task_b': 'shortest_path',
    'task_c': 'shortest_path',
    'default': 'shortest_path',
}

TASK_PRIORITY_MAP = {
    'task_0': 30,
    'task_1': 20,
    'task_2': 10,
    'task_a': 30,
    'task_b': 20,
    'task_c': 10,
    'default': 1,
}
