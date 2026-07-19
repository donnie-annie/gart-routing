"""Flask routes for the controller dashboard and REST API."""

import json
import logging
import traceback
from datetime import datetime

from flask import jsonify, make_response, request


logger = logging.getLogger("server_agent")


def _normalize_switch_id(raw):
    """Normalize a switch ID to an integer when possible."""
    if raw is None:
        return None
    if isinstance(raw, int):
        return raw
    try:
        return int(str(raw), 0)
    except (TypeError, ValueError):
        return raw


def _extract_flow_payload(data):
    """Validate and normalize a manual flow request."""
    if not isinstance(data, dict):
        return None, "请求体必须是 JSON 对象"

    switch_id = _normalize_switch_id(data.get('switch_id'))
    out_port = data.get('out_port')
    priority = data.get('priority', 10)
    idle_timeout = data.get('idle_timeout', 0)
    hard_timeout = data.get('hard_timeout', 0)
    match = data.get('match') or {}

    if switch_id in (None, ''):
        return None, "缺少 switch_id"
    try:
        out_port = int(out_port)
        priority = int(priority)
        idle_timeout = int(idle_timeout)
        hard_timeout = int(hard_timeout)
    except (TypeError, ValueError):
        return None, "out_port / priority / idle_timeout / hard_timeout 必须是整数"

    if not isinstance(match, dict):
        return None, "match 必须是对象"

    normalized_match = {}
    for key, value in match.items():
        if value is None or value == '':
            continue
        try:
            if key in ('eth_type', 'ip_proto'):
                normalized_match[str(key)] = int(value, 0) if isinstance(value, str) else int(value)
            elif key in ('in_port', 'tcp_src', 'tcp_dst', 'udp_src', 'udp_dst'):
                normalized_match[str(key)] = int(value)
            else:
                normalized_match[str(key)] = value
        except (TypeError, ValueError):
            return None, f"match 字段 {key} 的值无效"

    payload = {
        'switch_id': switch_id,
        'out_port': out_port,
        'priority': priority,
        'idle_timeout': idle_timeout,
        'hard_timeout': hard_timeout,
        'match': normalized_match,
    }
    return payload, None


def _safe_switch_key(switch_id):
    """Return a stable graph key for an optional switch ID."""
    return switch_id if switch_id is not None else ''


def _prepare_node_data_for_graph(node_data, include_flows=False):
    """Prepare node payload for /api/graph without shipping heavy flow tables by default."""
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


def register_web_api_routes(app, get_server_agent):
    """Register dashboard and API routes on a Flask application."""

    @app.route('/')
    def index():
        server_agent = get_server_agent()
        if server_agent is None:
            return '<h1>服务器未初始化</h1>', 503
        response = make_response(server_agent._get_web_ui_html())
        response.headers['Cache-Control'] = 'no-store, no-cache, must-revalidate, max-age=0'
        response.headers['Pragma'] = 'no-cache'
        response.headers['Expires'] = '0'
        return response

    @app.route('/api/health', methods=['GET'])
    def health_check():
        server_agent = get_server_agent()
        if server_agent is None:
            return jsonify({'error': 'Server not initialized'}), 503
        return jsonify({
            'status': 'ok',
            'controllers': len(server_agent.clients),
            'graph_nodes': len(server_agent.G.nodes()),
            'graph_edges': len(server_agent.G.edges())
        })

    @app.route('/api/topo', methods=['GET'])
    def get_topo():
        server_agent = get_server_agent()
        if server_agent is None:
            return jsonify({'error': 'Server not initialized'}), 503

        topo_data = {
            'switches': [],
            'links': [],
            'hosts': [],
            'last_update': datetime.now().strftime('%Y-%m-%d %H:%M:%S')
        }

        for switches in server_agent.controller_to_switches.values():
            topo_data['switches'].extend(switches)
        topo_data['switches'] = list(set(topo_data['switches']))

        for links in server_agent.topo.values():
            topo_data['links'].extend(links)

        for hosts in server_agent.host.values():
            topo_data['hosts'].extend(hosts)

        return jsonify(topo_data)

    @app.route('/api/controllers', methods=['GET'])
    def get_controllers():
        server_agent = get_server_agent()
        if server_agent is None:
            return jsonify({'error': 'Server not initialized'}), 503

        controller_switches_str = {}
        for key, switches in server_agent.controller_to_switches.items():
            if isinstance(key, tuple):
                key_str = f"{key[0]}:{key[1]}"
            else:
                key_str = str(key)
            controller_switches_str[key_str] = switches

        controllers_data = {
            'active_controllers': [f"{addr[0]}:{addr[1]}" if isinstance(addr, tuple) else str(addr)
                                   for addr in server_agent.clients.keys()],
            'controller_switches': controller_switches_str
        }
        return jsonify(controllers_data)

    @app.route('/api/graph', methods=['GET'])
    def get_graph():
        server_agent = get_server_agent()
        if server_agent is None:
            return jsonify({'error': 'Server not initialized'}), 503

        try:
            include_flows = str(request.args.get('include_flows', '0')).lower() in ('1', 'true', 'yes')
            snapshot = server_agent.web_state.get_graph_snapshot(include_flows=include_flows)
            graph_data = {
                'nodes': snapshot.get('nodes', []),
                'edges': snapshot.get('edges', []),
                'versions': snapshot.get('versions', {}),
            }

            logger.debug(
                "API /api/graph 返回: %s 个节点, %s 条边, versions=%s",
                len(graph_data['nodes']),
                len(graph_data['edges']),
                graph_data['versions'],
            )
            return jsonify(graph_data)
        except Exception as e:
            logger.error(f"API /api/graph 错误: {e}")
            logger.error(traceback.format_exc())
            return jsonify({'error': str(e), 'nodes': [], 'edges': [], 'versions': {}}), 500

    @app.route('/api/switch/<switch_id>/flows', methods=['GET'])
    def get_switch_flows(switch_id):
        server_agent = get_server_agent()
        if server_agent is None:
            return jsonify({'error': 'Server not initialized'}), 503

        sid = _normalize_switch_id(switch_id)
        try:
            return jsonify(server_agent.web_state.get_switch_flows(sid))
        except Exception as e:
            logger.error("API /api/switch/%s/flows 错误: %s", switch_id, e)
            return jsonify({'error': str(e), 'switch_id': switch_id, 'flows': []}), 500

    @app.route('/api/route_sessions', methods=['GET'])
    def get_route_sessions():
        server_agent = get_server_agent()
        if server_agent is None:
            return jsonify({'error': 'Server not initialized'}), 503

        dedup = {}
        route_store = getattr(server_agent, 'controller_route_sessions', {}) or {}
        for controller_key, items in route_store.items():
            if isinstance(controller_key, tuple):
                controller_id = f"{controller_key[0]}:{controller_key[1]}"
            else:
                controller_id = str(controller_key)
            if not isinstance(items, list):
                continue
            for raw in items:
                if not isinstance(raw, dict):
                    continue
                src_ip = raw.get('src_ip')
                dst_ip = raw.get('dst_ip')
                switch_path_raw = raw.get('switch_path') or []
                switch_path = []
                for node in switch_path_raw:
                    sid = _normalize_switch_id(node)
                    if sid is not None:
                        switch_path.append(sid)
                display_parts = []
                if src_ip:
                    display_parts.append(f"Host({src_ip})")
                display_parts.extend(str(x) for x in switch_path)
                if dst_ip:
                    display_parts.append(f"Host({dst_ip})")
                if not display_parts:
                    display_parts = ["-"]
                display_path = " -> ".join(display_parts)
                sess = {
                    'id': f"{controller_id}#{raw.get('session_id')}",
                    'session_id': raw.get('session_id'),
                    'controller': controller_id,
                    'switch_path': switch_path,
                    'display_path': display_path,
                    'src_ip': src_ip,
                    'dst_ip': dst_ip,
                    'task_type': raw.get('task_type', 'default'),
                    'route_policy': raw.get('route_policy', 'shortest_path'),
                    'l4_match': raw.get('l4_match'),
                    'path_source': raw.get('path_source', 'unknown'),
                    'decision_source': raw.get('decision_source', raw.get('path_source', 'unknown')),
                    'model_used': raw.get('model_used', False),
                    'fallback_reason': raw.get('fallback_reason'),
                    'model_confidence': raw.get('model_confidence'),
                    'drl_compute_time': raw.get('drl_compute_time'),
                    'drl_shadow': raw.get('drl_shadow'),
                    'created_at': raw.get('created_at', 0),
                    'updated_at': raw.get('updated_at', raw.get('created_at', 0)),
                }
                l4_key = json.dumps(sess.get('l4_match') or {}, sort_keys=True, ensure_ascii=False)
                dedup_key = (
                    sess['src_ip'],
                    sess['dst_ip'],
                    sess['task_type'],
                    sess['route_policy'],
                    l4_key,
                )
                prev = dedup.get(dedup_key)
                if prev is None or (sess.get('updated_at') or 0) >= (prev.get('updated_at') or 0):
                    dedup[dedup_key] = sess

        sessions = list(dedup.values())
        sessions.sort(key=lambda x: (x.get('updated_at') or 0, x.get('created_at') or 0), reverse=True)
        return jsonify({'sessions': sessions})

    @app.route('/api/path', methods=['POST'])
    def calculate_path():
        server_agent = get_server_agent()
        if server_agent is None:
            return jsonify({'error': 'Server not initialized'}), 503

        data = request.get_json()
        src = data.get('src')
        dst = data.get('dst')

        if not src or not dst:
            return jsonify({'error': '需要提供源和目的节点'}), 400

        try:
            path = server_agent.handle_path_request({'src': src, 'dst': dst})
            return jsonify({'path': path})
        except Exception as e:
            return jsonify({'error': str(e)}), 500

    @app.route('/api/statistics', methods=['GET'])
    def get_statistics():
        server_agent = get_server_agent()
        if server_agent is None:
            return jsonify({'error': 'Server not initialized'}), 503

        stats = {
            'controllers': len(server_agent.clients),
            'switches': sum(len(switches) for switches in server_agent.controller_to_switches.values()),
            'links': sum(len(links) for links in server_agent.topo.values()),
            'hosts': sum(len(hosts) for hosts in server_agent.host.values()),
            'graph_nodes': len(server_agent.G.nodes()),
            'graph_edges': len(server_agent.G.edges()),
            'dashboard': {
                'controllers': len(server_agent.clients),
                'switches': sum(len(switches) for switches in server_agent.controller_to_switches.values()),
                'hosts': sum(len(hosts) for hosts in server_agent.host.values()),
                'links': sum(len(links) for links in server_agent.topo.values()),
                'link_down': len(getattr(server_agent, 'link_down_set', {})) // 2,
            },
            'drl': {
                'enabled': True,
                'path_service_host': getattr(server_agent, 'path_service_host', '127.0.0.1'),
                'path_service_port': getattr(server_agent, 'path_service_port', 8889),
                'connected': getattr(server_agent, 'path_service_sock', None) is not None,
            }
        }
        return jsonify(stats)

    @app.route('/api/flows', methods=['POST'])
    def add_manual_flow():
        server_agent = get_server_agent()
        if server_agent is None:
            return jsonify({'error': 'Server not initialized'}), 503

        payload, err = _extract_flow_payload(request.get_json(silent=True))
        if err:
            return jsonify({'error': err}), 400

        try:
            result = server_agent.add_manual_flow(payload)
            status = 200 if result.get('status') == 'ok' else 400
            return jsonify(result), status
        except Exception as e:
            logger.error("API /api/flows POST 错误: %s", e)
            logger.error(traceback.format_exc())
            return jsonify({'status': 'error', 'message': str(e)}), 500

    @app.route('/api/flows', methods=['DELETE'])
    def delete_manual_flow():
        server_agent = get_server_agent()
        if server_agent is None:
            return jsonify({'error': 'Server not initialized'}), 503

        data = request.get_json(silent=True) or {}
        switch_id = _normalize_switch_id(data.get('switch_id'))
        flow_id = data.get('flow_id')
        if switch_id in (None, '') or flow_id in (None, ''):
            return jsonify({'error': '缺少 switch_id 或 flow_id'}), 400

        try:
            result = server_agent.delete_manual_flow(switch_id, flow_id)
            status = 200 if result.get('status') == 'ok' else 400
            return jsonify(result), status
        except Exception as e:
            logger.error("API /api/flows DELETE 错误: %s", e)
            logger.error(traceback.format_exc())
            return jsonify({'status': 'error', 'message': str(e)}), 500
