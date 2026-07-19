"""
Versioned Web state snapshots for the Flask UI.

The server_agent owns the live topology and controller caches. This module
builds small, reusable API payloads from that state so frequent Web refreshes do
not repeatedly walk and serialize the same NetworkX graph.
"""

import json
import threading


class WebStateStore:
    def __init__(self, server_agent):
        self.server_agent = server_agent
        self._lock = threading.RLock()
        self.topology_version = 0
        self.route_sessions_version = 0
        self.flow_versions = {}
        self._graph_cache = {}

    def mark_topology_dirty(self):
        with self._lock:
            self.topology_version += 1
            self._graph_cache.clear()

    def mark_route_sessions_dirty(self):
        with self._lock:
            self.route_sessions_version += 1

    def mark_switch_flows_dirty(self, switch_id):
        with self._lock:
            sid = self.server_agent._normalize_switch_id(switch_id)
            self.flow_versions[sid] = self.flow_versions.get(sid, 0) + 1
            self._graph_cache.clear()

    def versions(self):
        with self._lock:
            return {
                'topology': self.topology_version,
                'route_sessions': self.route_sessions_version,
                'flows': sum(self.flow_versions.values()),
            }

    def get_switch_flows(self, switch_id):
        sid = self.server_agent._normalize_switch_id(switch_id)
        flows = self.server_agent._get_switch_flow_table(sid)
        with self._lock:
            version = self.flow_versions.get(sid, 0)
        return {
            'switch_id': sid,
            'flows': flows,
            'flow_count': len(flows),
            'version': version,
        }

    def get_graph_snapshot(self, include_flows=False):
        include_flows = bool(include_flows)
        with self._lock:
            cache_key = include_flows
            cache_version = (
                self.topology_version,
                sum(self.flow_versions.values()),
                self.route_sessions_version,
            )
            cached = self._graph_cache.get(cache_key)
            if cached and cached.get('version') == cache_version:
                return dict(cached['payload'])

        payload = self._build_graph_payload(include_flows=include_flows)
        with self._lock:
            payload['versions'] = self.versions()
            self._graph_cache[include_flows] = {
                'version': cache_version,
                'payload': dict(payload),
            }
        return payload

    def _build_graph_payload(self, include_flows=False):
        graph = self.server_agent.G
        nodes_list = []
        for node_id, node_data in graph.nodes(data=True):
            safe_id = _json_safe_value(node_id)
            node_type = node_data.get('node_type', 'unknown')
            neighbors = list(graph.neighbors(node_id))
            connection_counts = {}

            if node_type == 'root_controller':
                connection_counts['controllers'] = sum(
                    1 for n in neighbors
                    if graph.nodes[n].get('node_type') == 'controller'
                )
            elif node_type == 'controller':
                connection_counts['switches'] = sum(
                    1 for n in neighbors
                    if graph.nodes[n].get('node_type') == 'switch'
                )
            elif node_type == 'switch':
                connection_counts['hosts'] = sum(
                    1 for n in neighbors
                    if graph.nodes[n].get('node_type') == 'host'
                )

            node_payload = _prepare_node_data_for_graph(node_data, include_flows=include_flows)
            node_payload['connection_counts'] = connection_counts
            nodes_list.append({'id': safe_id, 'data': node_payload})

        edges_list = []
        for src, dst, edge_data in graph.edges(data=True):
            edge_dict = {
                'source': _json_safe_value(src),
                'target': _json_safe_value(dst),
                'data': {},
            }
            for key, value in (edge_data or {}).items():
                edge_dict['data'][key] = _json_safe_value(value)
            edges_list.append(edge_dict)

        return {
            'nodes': nodes_list,
            'edges': edges_list,
        }


def _json_safe_value(value):
    try:
        json.dumps(value)
        return value
    except (TypeError, ValueError):
        return str(value)


def _prepare_node_data_for_graph(node_data, include_flows=False):
    out = dict(node_data or {})
    flow_table = out.get('flow_table', []) or []
    out['flow_count'] = len(flow_table) if isinstance(flow_table, list) else 0
    if include_flows:
        out['flow_table'] = flow_table if isinstance(flow_table, list) else []
    else:
        out.pop('flow_table', None)
    if out.get('node_type') == 'switch':
        out['gateway_ip'] = out.get('gateway_ip', '')
    return out
