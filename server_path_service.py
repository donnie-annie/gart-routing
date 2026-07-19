"""
Path calculation helpers for the deliverable server_agent.

The server tries the external DRL path_service first, then falls back to
policy-aware Dijkstra on the current global graph.
"""

import networkx as nx

from routing_policy import compute_edge_weight


def _is_switch_node(node):
    return isinstance(node, int)


def build_topo_edges_for_path_service(graph, link_down_set=None, route_policy='shortest_path'):
    """Build dynamic capacity/delay/loss edges consumed by GART.

    ``weight`` is retained for Dijkstra and legacy path-service compatibility.
    """
    link_down_set = link_down_set or {}
    topo_edges = []
    for src, dst, data in graph.edges(data=True):
        if not _is_switch_node(src) or not _is_switch_node(dst):
            continue
        if data.get('status') == 'down' or (src, dst) in link_down_set:
            continue
        capacity = float(data.get('capacity', data.get('bw', data.get('bandwidth', 1.0))))
        utilization = float(data.get('utilization', 0.0))
        if utilization > 1.0:
            utilization /= 100.0
        utilization = max(0.0, min(utilization, 1.0))
        available_bandwidth = float(data.get(
            'available_bandwidth',
            data.get('residual_bandwidth', capacity * (1.0 - utilization)),
        ))
        topo_edges.append({
            'src': int(src),
            'dst': int(dst),
            'weight': compute_edge_weight(route_policy, data),
            'capacity': capacity,
            'available_bandwidth': max(available_bandwidth, 0.0),
            'delay': float(data.get('delay', data.get('latency', data.get('weight', 1.0)))),
            'loss': float(data.get('loss', data.get('loss_rate', 0.0))),
            'utilization': utilization,
            'status': data.get('status', 'up'),
        })
    return topo_edges


def build_hop_ports(graph, path):
    """Return {"src->dst": out_port} for every switch-to-switch hop in path."""
    hop_ports = {}
    for src, dst in zip(path, path[1:]):
        if not _is_switch_node(src) or not _is_switch_node(dst):
            continue
        data = graph.get_edge_data(src, dst, default={}) or {}
        port = (
            data.get('src_port')
            or data.get('port')
            or data.get('out_port')
            or data.get('src_port_no')
        )
        if port is not None:
            hop_ports["%d->%d" % (src, dst)] = port
    return hop_ports


def validate_switch_path(graph, full_path):
    """Validate host-switch path shape and switch adjacency."""
    if not full_path or len(full_path) < 3:
        return False, 'path too short'
    switch_path = [node for node in full_path if _is_switch_node(node)]
    if not switch_path:
        return False, 'path has no switch nodes'
    for src, dst in zip(switch_path, switch_path[1:]):
        if not graph.has_edge(src, dst):
            return False, 'missing edge %s->%s' % (src, dst)
    return True, 'ok'


def summarize_path_metrics(graph, path):
    """Summarize switch-link metrics for a candidate path."""
    switch_edges = []
    for src, dst in zip(path, path[1:]):
        data = graph.get_edge_data(src, dst, default={}) or {}
        if data.get('edge_type') == 'switch_link' or (_is_switch_node(src) and _is_switch_node(dst)):
            switch_edges.append(data)

    delay = sum(float(edge.get('delay', edge.get('weight', 1))) for edge in switch_edges)
    success_prob = 1.0
    bandwidths = []
    utilization = []
    for edge in switch_edges:
        success_prob *= 1.0 - max(float(edge.get('loss', 0)), 0.0)
        if 'bw' in edge:
            bandwidths.append(float(edge.get('bw', 0)))
        if 'utilization' in edge:
            utilization.append(float(edge.get('utilization', 0)))

    return {
        'hop_count': max(len(path) - 1, 0),
        'switch_hop_count': len(switch_edges),
        'delay': delay,
        'loss': max(0.0, 1.0 - success_prob),
        'min_bandwidth': min(bandwidths) if bandwidths else None,
        'max_utilization': max(utilization) if utilization else None,
    }


def build_k_shortest_candidates(graph, src, dst, k=5, link_down_set=None, route_policy='shortest_path'):
    """Build up to k weighted simple path candidates with metrics."""
    link_down_set = link_down_set or set()
    candidate_graph = graph.copy()
    for u, v in link_down_set:
        if candidate_graph.has_edge(u, v):
            candidate_graph.remove_edge(u, v)

    def _weight(u, v, data):
        return compute_edge_weight(route_policy, data)

    try:
        paths_iter = nx.shortest_simple_paths(candidate_graph, src, dst, weight=_weight)
        candidates = []
        for path_id, path in enumerate(paths_iter):
            path = list(path)
            candidates.append({
                'path_id': path_id,
                'path': path,
                'switch_path': [node for node in path if _is_switch_node(node)],
                'metrics': summarize_path_metrics(graph, path),
            })
            if len(candidates) >= max(int(k), 1):
                break
        return candidates
    except (nx.NetworkXNoPath, nx.NodeNotFound):
        return []


def handle_path_request_with_policy(graph, message, link_down_set=None):
    """Compute a fallback path with the hydrate routing policy model."""
    src = message.get('src')
    dst = message.get('dst')
    task_type = message.get('task_type', 'default')
    route_policy = message.get('route_policy', 'shortest_path')
    link_down_set = link_down_set or {}

    if not src or not dst:
        return {'status': 'error', 'message': 'path request missing src or dst'}

    if src not in graph or dst not in graph:
        return {'status': 'error', 'message': 'src or dst not in graph'}

    try:
        fallback_graph = graph.copy()
        for u, v in link_down_set:
            if fallback_graph.has_edge(u, v):
                fallback_graph.remove_edge(u, v)
        path = nx.shortest_path(
            fallback_graph,
            src,
            dst,
            weight=lambda u, v, data: compute_edge_weight(route_policy, data)
        )
        out = {
            'status': 'ok',
            'path': path,
            'src_ip': src,
            'dst_ip': dst,
            'switch_id': message.get('switch_id'),
            'in_port': message.get('in_port'),
            'task_type': task_type,
            'route_policy': route_policy,
            'path_source': 'dijkstra',
            'hop_ports': build_hop_ports(graph, path),
        }
        if 'l4_match' in message:
            out['l4_match'] = message['l4_match']
        if 'session_id' in message:
            out['session_id'] = message.get('session_id')
        return out
    except nx.NetworkXNoPath:
        return {'status': 'error', 'message': 'no path from %s to %s' % (src, dst)}
    except Exception as exc:
        return {'status': 'error', 'message': 'path calculation failed: %s' % exc}
