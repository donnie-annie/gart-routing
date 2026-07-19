#!/usr/bin/env python3
"""Audit Web graph and route-session consistency.

This script is intentionally dependency-free so it can run on the Linux
test server even when pytest or browser tooling is unavailable.
"""

from __future__ import annotations

import argparse
import json
import sys
import urllib.request
from typing import Any


def _sid(value: Any) -> str:
    return str(value)


def _link_key(a: Any, b: Any) -> str:
    x, y = _sid(a), _sid(b)
    return "||".join(sorted((x, y)))


def fetch_json(base_url: str, path: str) -> dict[str, Any]:
    url = base_url.rstrip("/") + path
    with urllib.request.urlopen(url, timeout=10) as response:
        return json.loads(response.read().decode("utf-8"))


def audit_payloads(graph: dict[str, Any], route_sessions: dict[str, Any]) -> list[str]:
    errors: list[str] = []
    nodes = graph.get("nodes") or []
    edges = graph.get("edges") or []
    sessions = route_sessions.get("sessions") or []

    switches = {
        _sid(node.get("id"))
        for node in nodes
        if (node.get("data") or {}).get("node_type") == "switch"
    }
    if not switches:
        errors.append("graph has no switch nodes")

    switch_links: set[str] = set()
    for edge in edges:
        edge_data = edge.get("data") or {}
        if edge_data.get("edge_type") != "switch_link":
            continue
        source = _sid(edge.get("source"))
        target = _sid(edge.get("target"))
        if source not in switches:
            errors.append(f"switch_link source {source} is not a switch node")
        if target not in switches:
            errors.append(f"switch_link target {target} is not a switch node")
        switch_links.add(_link_key(source, target))

    for session in sessions:
        session_id = session.get("id", "<unknown>")
        path = [_sid(item) for item in (session.get("switch_path") or [])]
        if not path:
            errors.append(f"route session {session_id} has empty switch_path")
            continue
        for node_id in path:
            if node_id not in switches:
                errors.append(f"route session {session_id} references missing switch {node_id}")
        for left, right in zip(path, path[1:]):
            key = _link_key(left, right)
            if key not in switch_links:
                errors.append(f"route session {session_id} missing switch_link {left}<->{right}")

    return errors


def main() -> int:
    parser = argparse.ArgumentParser(description="Audit Web graph/route-session consistency")
    parser.add_argument("--base-url", default="http://127.0.0.1:6009")
    args = parser.parse_args()

    graph = fetch_json(args.base_url, "/api/graph?include_flows=0")
    sessions = fetch_json(args.base_url, "/api/route_sessions")
    errors = audit_payloads(graph, sessions)
    if errors:
        print("Web consistency audit failed:")
        for error in errors:
            print(f"- {error}")
        return 1

    print(
        "Web consistency audit ok: "
        f"{len(graph.get('nodes') or [])} nodes, "
        f"{len(graph.get('edges') or [])} edges, "
        f"{len(sessions.get('sessions') or [])} route sessions"
    )
    return 0


if __name__ == "__main__":
    sys.exit(main())
