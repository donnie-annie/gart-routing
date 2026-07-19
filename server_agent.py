#!/usr/bin/env python3

import sys
import argparse
import logging
import json
import socket
import threading
import time
import signal
import os
import networkx as nx
import traceback
from flask import Flask
try:
    from flask_cors import CORS
except ImportError:
    def CORS(*args, **kwargs):
        return None
from common_config import (
    CONTROLLER_IP,
    CONTROLLER_PORT,
    WEB_PORT,
    PATH_SERVICE_HOST,
    PATH_SERVICE_PORT,
    DRL_ROUTE_MODE,
    DRL_K_CANDIDATES,
    get_gart_flow_profile,
)
from server_path_service import (
    build_k_shortest_candidates,
    build_hop_ports,
    build_topo_edges_for_path_service,
    handle_path_request_with_policy,
    validate_switch_path,
)
from web_api import register_web_api_routes
from web_ui_html import get_web_ui_html
from web_state_store import WebStateStore
from server_message_handlers import (
    process_message as process_message_handler,
    heartbeat_check_loop as heartbeat_check_loop_handler,
    cleanup_disconnected_client as cleanup_disconnected_client_handler,
)

LOG_DIR = os.path.join(os.path.dirname(os.path.abspath(__file__)), "logs")
os.makedirs(LOG_DIR, exist_ok=True)
SERVER_AGENT_LOG_FILE = os.path.join(LOG_DIR, "server_agent.log")

logging.basicConfig(
    level=getattr(logging, os.environ.get("SERVER_AGENT_LOG_LEVEL", "INFO").upper(), logging.INFO),
    format='%(asctime)s [%(levelname)s] %(message)s',
    handlers=[
        logging.StreamHandler(),
        logging.FileHandler(SERVER_AGENT_LOG_FILE, mode='w', encoding='utf-8')
    ]
)
logger = logging.getLogger("server_agent")

app = Flask(__name__)

CORS(app, resources={r"/api/*": {"origins": "*"}})

server_agent = None

def _get_server_agent():
    return server_agent


register_web_api_routes(app, _get_server_agent)

VALID_DRL_ROUTE_MODES = ("spf", "shadow", "hybrid", "drl")


def parse_route_mode_arg(argv=None):
    parser = argparse.ArgumentParser(
        description="Start server_agent with an optional DRL route mode."
    )
    parser.add_argument(
        "route_mode",
        nargs="?",
        default=DRL_ROUTE_MODE,
        type=str.lower,
        choices=VALID_DRL_ROUTE_MODES,
        help="Routing mode: spf, shadow, hybrid, or drl.",
    )
    return parser.parse_args(argv).route_mode


class ServerAgent:
    def __init__(self, ip, port, route_mode=None):
        self.ip = ip
        self.port = port
        self.route_mode = route_mode or DRL_ROUTE_MODE
        self.sock = None
        self.is_running = False
        self.clients = {}
        self.client_last_heartbeat = {}
        self.client_lock = threading.Lock()

        self.heartbeat_interval = 2
        self.heartbeat_timeout = 6

        self.topo = {}
        self.host = {}
        self.controller_to_switches = {}
        self.controller_route_sessions = {}
        self.switch_flow_tables = {}
        self.web_state = WebStateStore(self)

        self.portdata_query_requests = {}

        self.G = nx.DiGraph()
        self.path_service_sock = None
        self.path_service_host = PATH_SERVICE_HOST
        self.path_service_port = PATH_SERVICE_PORT
        self.path_service_lock = threading.Lock()
        self.pending_path_installs = {}
        self.path_install_cond = threading.Condition()
        self.link_down_set = {}
        self.LINK_DOWN_TTL = 30
        self._connect_path_service()

        self.print_thread = threading.Thread(target=self.print_topo_info_loop)
        self.print_thread.daemon = True
        self.print_thread.start()

        self.heartbeat_thread = threading.Thread(target=self.heartbeat_check_loop)
        self.heartbeat_thread.daemon = True
        self.heartbeat_thread.start()

        logger.info("初始化完成，定时打印线程已启动，心跳检测线程已启动")

    def _get_web_ui_html(self):
        return get_web_ui_html()

    @staticmethod
    def _normalize_switch_id(raw):
        if raw is None:
            return None
        if isinstance(raw, int):
            return raw
        try:
            return int(str(raw), 0)
        except (TypeError, ValueError):
            return raw

    def _find_controller_for_switch(self, switch_id):
        for controller_key, switches in self.controller_to_switches.items():
            if switch_id in switches:
                return controller_key
        return None

    def _set_switch_flow_table(self, switch_id, flow_table):
        sid = self._normalize_switch_id(switch_id)
        self.switch_flow_tables[sid] = list(flow_table or [])
        if sid in self.G.nodes:
            self.G.nodes[sid]['flow_table'] = list(self.switch_flow_tables[sid])
        if hasattr(self, 'web_state'):
            self.web_state.mark_switch_flows_dirty(sid)

    def _get_switch_flow_table(self, switch_id):
        sid = self._normalize_switch_id(switch_id)
        return list(self.switch_flow_tables.get(sid, []))

    def add_manual_flow(self, payload):
        switch_id = self._normalize_switch_id(payload.get('switch_id'))
        out_port = payload.get('out_port')
        priority = payload.get('priority', 10)
        idle_timeout = payload.get('idle_timeout', 0)
        hard_timeout = payload.get('hard_timeout', 0)
        match = payload.get('match', {})

        controller = self._find_controller_for_switch(switch_id)
        if controller is None:
            return {'status': 'error', 'message': f'未找到管理交换机 {switch_id} 的控制器'}

        flow_id = int(time.time() * 1000)
        flow_entry = {
            'id': flow_id,
            'priority': priority,
            'match': json.dumps(match, ensure_ascii=False, sort_keys=True),
            'action': f'OUTPUT:{out_port}',
            'packets': 0,
            'manual': True,
            'match_dict': match,
            'out_port': out_port,
            'idle_timeout': idle_timeout,
            'hard_timeout': hard_timeout,
        }

        flow_table = self._get_switch_flow_table(switch_id)
        flow_table.append(flow_entry)
        self._set_switch_flow_table(switch_id, flow_table)

        msg = {
            'type': 'manual_flow_mod',
            'op': 'add',
            'switch_id': switch_id,
            'flow_id': flow_id,
            'priority': priority,
            'match': match,
            'out_port': out_port,
            'idle_timeout': idle_timeout,
            'hard_timeout': hard_timeout,
        }
        self._send_to_controller(controller, msg)
        logger.info("手动流表下发请求: switch=%s, flow_id=%s, match=%s, out_port=%s",
                    switch_id, flow_id, match, out_port)
        return {'status': 'ok', 'flow': flow_entry}

    def delete_manual_flow(self, switch_id, flow_id):
        switch_id = self._normalize_switch_id(switch_id)
        if switch_id not in self.switch_flow_tables:
            return {'status': 'error', 'message': f'交换机 {switch_id} 不存在'}
        flow_table = self._get_switch_flow_table(switch_id)
        flow_idx = None
        flow_obj = None
        for idx, flow in enumerate(flow_table):
            if str(flow.get('id')) == str(flow_id):
                flow_idx = idx
                flow_obj = flow
                break

        if flow_idx is None:
            return {'status': 'error', 'message': f'未找到 flow_id={flow_id} 的规则'}

        del flow_table[flow_idx]
        self._set_switch_flow_table(switch_id, flow_table)

        controller = self._find_controller_for_switch(switch_id)
        if controller is not None:
            msg = {
                'type': 'manual_flow_mod',
                'op': 'delete',
                'switch_id': switch_id,
                'flow_id': flow_obj.get('id'),
                'priority': int(flow_obj.get('priority', 10)),
                'match': flow_obj.get('match_dict', {}),
            }
            self._send_to_controller(controller, msg)

        logger.info("手动删除流表请求: switch=%s, flow_id=%s", switch_id, flow_id)
        return {'status': 'ok', 'flow_id': flow_id}

    def handle_flow_removed(self, client_addr, message):
        switch_id = self._normalize_switch_id(message.get('switch_id'))
        priority = int(message.get('priority', 0))
        match = message.get('match') or {}

        old_table = self._get_switch_flow_table(switch_id)
        new_table = [
            flow for flow in old_table
            if not (
                int(flow.get('priority', 0)) == priority and
                flow.get('match_dict', {}) == match
            )
        ]
        self._set_switch_flow_table(switch_id, new_table)

        removed_sessions = set(message.get('removed_sessions') or [])
        route_sessions = self.controller_route_sessions.get(client_addr)
        if isinstance(route_sessions, list) and removed_sessions:
            self.controller_route_sessions[client_addr] = [
                session for session in route_sessions
                if session.get('session_id') not in removed_sessions
            ]
            self.web_state.mark_route_sessions_dirty()

        logger.info(
            "flow_removed cached: controller=%s switch=%s priority=%s reason=%s removed=%s",
            client_addr, switch_id, priority, message.get('reason'), len(old_table) - len(new_table)
        )

    def start_web_server(self):
        def run_flask():
            try:
                import logging
                log = logging.getLogger('werkzeug')
                log.setLevel(logging.WARNING)

                logger.info(f"Flask线程开始运行，准备绑定端口 {WEB_PORT}")
                print(f"Flask线程开始运行，准备绑定端口 {WEB_PORT}")

                app.run(host='0.0.0.0', port=WEB_PORT, debug=False, use_reloader=False, threaded=True)
            except Exception as e:
                logger.error(f"Flask Web服务器启动失败: {e}")
                logger.error(traceback.format_exc())
                print(f"Flask Web服务器启动失败: {e}")
                print(traceback.format_exc())

        web_thread = threading.Thread(target=run_flask, daemon=True)
        web_thread.start()

        time.sleep(1)

        logger.info(f"Web 服务器线程已启动（端口 {WEB_PORT}）")
        logger.info(f"访问 http://localhost:{WEB_PORT} 查看拓扑可视化")
        print(f"Web 服务器线程已启动（端口 {WEB_PORT}）")
        print(f"访问 http://localhost:{WEB_PORT} 查看拓扑可视化")

    def start(self):
        try:
            self.start_web_server()

            self.sock = socket.socket(socket.AF_INET, socket.SOCK_STREAM)
            self.sock.setsockopt(socket.SOL_SOCKET, socket.SO_REUSEADDR, 1)
            self.sock.bind((self.ip, self.port))
            self.sock.listen(5)
            self.is_running = True

            logger.info(f"服务器已启动，监听地址: {self.ip}:{self.port}")
            print(f"服务器已启动，监听地址: {self.ip}:{self.port}")

            while self.is_running:
                try:
                    client_sock, client_addr = self.sock.accept()
                    logger.info(f"接受连接: {client_addr}")

                    client_thread = threading.Thread(
                        target=self.handle_client,
                        args=(client_sock, client_addr)
                    )
                    client_thread.daemon = True
                    client_thread.start()

                    client_sock.settimeout(self.heartbeat_timeout)

                    with self.client_lock:
                        self.clients[client_addr] = (client_sock, client_thread)
                        self.client_last_heartbeat[client_addr] = time.time()

                except socket.timeout:
                    continue
                except Exception as e:
                    if self.is_running:
                        logger.error(f"接受连接时出错: {e}")
                        print(f"接受连接时出错: {e}")
        except Exception as e:
            logger.error(f"启动服务器时出错: {e}")
            print(f"启动服务器时出错: {e}")
        finally:
            self.stop()

    def handle_client(self, client_sock, client_addr):
        buffer = ""
        try:
            while self.is_running:
                try:
                    data = client_sock.recv(4096)
                    if not data:
                        logger.info(f"客户端 {client_addr} 关闭了连接")
                        print(f"客户端 {client_addr} 关闭了连接")
                        break

                    buffer += data.decode('utf-8')

                    while '\n' in buffer:
                        line, buffer = buffer.split('\n', 1)
                        line = line.strip()
                        if line:
                            try:
                                self.process_message(client_sock, client_addr, line.encode('utf-8'))
                            except Exception as e:
                                logger.error(f"处理消息时出错: {e}, 消息内容: {line[:100]}")
                                logger.error(traceback.format_exc())

                except socket.timeout:
                    continue
                except Exception as e:
                    logger.error(f"接收数据时出错: {e}")
                    logger.error(traceback.format_exc())
                    print(f"接收数据时出错: {e}")
                    break
        except Exception as e:
            logger.error(f"处理客户端 {client_addr} 时出错: {e}")
            logger.error(traceback.format_exc())
            print(f"处理客户端 {client_addr} 时出错: {e}")
        finally:
            self.cleanup_disconnected_client(client_addr, reason="连接关闭")

    def process_message(self, client_sock, client_addr, data):
        return process_message_handler(self, client_sock, client_addr, data)

    def new_method(self, client_addr, message):
        logger.debug(f"从 {client_addr} 接收到消息: {message}")

    def heartbeat_check_loop(self):
        return heartbeat_check_loop_handler(self)

    def cleanup_disconnected_client(self, client_addr, reason="未知"):
        return cleanup_disconnected_client_handler(self, client_addr, reason=reason)

    def handle_topo_message(self, client_addr, message):
        controller_key = client_addr if isinstance(client_addr, tuple) else (client_addr, 0)
        logger.info(f"处理来自 {controller_key} 的拓扑信息")

        if 'switches' in message:
            normalized_switches = []
            for sw in message['switches'] or []:
                sw_id = self._normalize_switch_id(sw)
                if sw_id is not None:
                    normalized_switches.append(sw_id)
            self.controller_to_switches[controller_key] = normalized_switches
            logger.info(f"更新控制器 {controller_key} 的交换机: {normalized_switches}")

        if 'switch_flow_tables' in message and isinstance(message['switch_flow_tables'], dict):
            for sw_key, flow_table in message['switch_flow_tables'].items():
                sw_id = self._normalize_switch_id(sw_key)
                self._set_switch_flow_table(sw_id, flow_table if isinstance(flow_table, list) else [])

        if 'link' in message:
            self.topo[controller_key] = message['link']
            logger.info(f"更新控制器 {controller_key} 的链路: {len(message['link'])} 条")

            for link in message['link']:
                logger.debug(f"链路详情: {link}")

        if 'host' in message:
            self.host[controller_key] = message['host']
            logger.info(f"更新控制器 {controller_key} 的主机: {len(message['host'])} 个")

            for host in message['host']:
                logger.debug(f"主机详情: {host}")

        route_sessions = message.get('route_sessions')
        if isinstance(route_sessions, list):
            self.controller_route_sessions[controller_key] = route_sessions
            self.web_state.mark_route_sessions_dirty()
            logger.info(f"更新控制器 {controller_key} 的路径会话: {len(route_sessions)} 条")

        self.update_graph()

        logger.info("拓扑信息处理完成")

    def handle_host_message(self, client_addr, message):
        controller_key = client_addr if isinstance(client_addr, tuple) else (client_addr, 0)
        if 'hosts' in message:
            self.host[controller_key] = message['hosts']
            logger.info(f"更新控制器 {controller_key} 的主机信息: {len(message['hosts'])} 个主机")

            self.update_graph()

    def handle_portdata_query(self, client_addr, message):
        src_dpid = message.get('src_dpid')
        request_id = message.get('request_id')

        logger.debug(f"收到PortData查询请求: src_dpid={src_dpid}, request_id={request_id}, 来自 {client_addr}")

        self.portdata_query_requests[request_id] = (client_addr, time.time())

        target_controller = None
        for controller_key, switches in self.controller_to_switches.items():
            if src_dpid in switches:
                target_controller = controller_key
                break

        if target_controller is None:
            logger.warning(f"未找到管理交换机 {src_dpid} 的控制器")
            error_response = {
                "type": "portdata_response",
                "request_id": request_id,
                "src_dpid": src_dpid,
                "status": "error",
                "message": f"Controller not found for switch {src_dpid}"
            }
            self._send_to_controller(client_addr, error_response)
            if request_id in self.portdata_query_requests:
                del self.portdata_query_requests[request_id]
            return

        if target_controller == client_addr:
            logger.warning(f"PortData查询请求的交换机属于请求控制器本身: {src_dpid}")
            if request_id in self.portdata_query_requests:
                del self.portdata_query_requests[request_id]
            return

        logger.debug(f"转发PortData查询请求到控制器 {target_controller}")
        self._send_to_controller(target_controller, message)

    def handle_portdata_response(self, client_addr, message):
        request_id = message.get('request_id')
        logger.debug(f"收到PortData查询响应: request_id={request_id}, 来自 {client_addr}")

        if request_id in self.portdata_query_requests:
            requester_addr, query_time = self.portdata_query_requests[request_id]

            logger.debug(f"转发PortData响应到请求控制器 {requester_addr}")
            self._send_to_controller(requester_addr, message)

            del self.portdata_query_requests[request_id]
        else:
            logger.warning(f"未找到PortData查询请求记录: request_id={request_id}")

    def handle_lldp_report(self, client_addr, message):
        src_dpid = message.get('src_dpid')
        dst_dpid = message.get('dst_dpid')
        send_time = message.get('send_time')
        receive_time = message.get('receive_time')
        src_echo = float(message.get('src_echo', 0.0) or 0.0)
        dst_echo = float(message.get('dst_echo', 0.0) or 0.0)

        if src_dpid is None or dst_dpid is None:
            logger.warning("LLDP报告缺少交换机信息: %s", message)
            return

        if send_time is None or receive_time is None:
            error_resp = {
                "type": "lldp_delay_update",
                "status": "error",
                "message": "send_time or receive_time missing",
                "src_dpid": src_dpid,
                "dst_dpid": dst_dpid
            }
            self._send_to_controller(client_addr, error_resp)
            return

        try:
            fwd_delay = float(receive_time) - float(send_time)
            calc_delay = fwd_delay - (src_echo + dst_echo) / 2
            calc_delay = max(calc_delay, 0.0)
        except Exception as e:
            logger.error(f"计算LLDP延迟失败: {e}")
            error_resp = {
                "type": "lldp_delay_update",
                "status": "error",
                "message": f"calc error: {e}",
                "src_dpid": src_dpid,
                "dst_dpid": dst_dpid
            }
            self._send_to_controller(client_addr, error_resp)
            return

        resp = {
            "type": "lldp_delay_update",
            "status": "ok",
            "src_dpid": src_dpid,
            "dst_dpid": dst_dpid,
            "fwd_delay": fwd_delay,
            "src_echo": src_echo,
            "dst_echo": dst_echo,
            "delay": calc_delay
        }

        self._send_to_controller(client_addr, resp)

        targets = set()
        for controller_key, switches in self.controller_to_switches.items():
            if src_dpid in switches or dst_dpid in switches:
                targets.add(controller_key)

        for target in targets:
            if target != client_addr:
                self._send_to_controller(target, resp)

        logger.debug(f"LLDP延迟计算完成并分发: {resp}, targets={targets}")

    def _send_to_controller(self, controller_addr, message):
        with self.client_lock:
            if controller_addr in self.clients:
                sock, _ = self.clients[controller_addr]
                try:
                    data = json.dumps(message, ensure_ascii=False) + '\n'
                    sock.sendall(data.encode('utf-8'))
                    logger.debug(f"向控制器 {controller_addr} 发送消息: {message.get('type')}")
                except Exception as e:
                    logger.error(f"向控制器 {controller_addr} 发送消息失败: {e}")
            else:
                logger.warning(f"控制器 {controller_addr} 未连接")

    def update_graph(self):
        self.G.clear()

        root_controller_id = "RootController"
        root_ip = self.ip if hasattr(self, 'ip') else '0.0.0.0'
        self.G.add_node(root_controller_id, node_type='root_controller', ip=root_ip)

        controller_keys = set()

        for client_addr in self.clients.keys():
            if isinstance(client_addr, tuple):
                controller_keys.add(client_addr)
            else:
                controller_keys.add((client_addr, 0))

        for controller_key in self.topo.keys():
            if isinstance(controller_key, tuple):
                controller_keys.add(controller_key)
            else:
                controller_keys.add((controller_key, 0))

        for controller_key in self.controller_to_switches.keys():
            if isinstance(controller_key, tuple):
                controller_keys.add(controller_key)
            else:
                controller_keys.add((controller_key, 0))

        for controller_key in self.host.keys():
            if isinstance(controller_key, tuple):
                controller_keys.add(controller_key)
            else:
                controller_keys.add((controller_key, 0))

        for controller_key in controller_keys:
            if isinstance(controller_key, tuple):
                ip, port = controller_key
                controller_id = f"Controller_{ip}_{port}"
            else:
                ip = controller_key
                port = 0
                controller_id = f"Controller_{ip}_{port}"

            self.G.add_node(controller_id, node_type='controller', ip=ip, port=port)
            self.G.add_edge(root_controller_id, controller_id,
                          edge_type='controller_connection', weight=1)
            logger.debug(f"添加控制器节点: {controller_id} (IP: {ip}, Port: {port})")

        for controller_key, links in self.topo.items():
            if isinstance(controller_key, tuple):
                ip, port = controller_key
                controller_id = f"Controller_{ip}_{port}"
            else:
                ip = controller_key
                port = 0
                controller_id = f"Controller_{ip}_{port}"

            if controller_id not in self.G:
                self.G.add_node(controller_id, node_type='controller', ip=ip, port=port)
                if root_controller_id in self.G:
                    self.G.add_edge(root_controller_id, controller_id,
                                  edge_type='controller_connection', weight=1)

            for link in links:
                src = link.get('src')
                dst = link.get('dst')
                if src and dst:
                    if src not in self.G:
                        self.G.add_node(src, node_type='switch', flow_table=self._get_switch_flow_table(src))
                    else:
                        if 'node_type' not in self.G.nodes[src] or self.G.nodes[src].get('node_type') != 'switch':
                            self.G.nodes[src]['node_type'] = 'switch'
                        self.G.nodes[src]['flow_table'] = self._get_switch_flow_table(src)

                    if dst not in self.G:
                        self.G.add_node(dst, node_type='switch', flow_table=self._get_switch_flow_table(dst))
                    else:
                        if 'node_type' not in self.G.nodes[dst] or self.G.nodes[dst].get('node_type') != 'switch':
                            self.G.nodes[dst]['node_type'] = 'switch'
                        self.G.nodes[dst]['flow_table'] = self._get_switch_flow_table(dst)

                    delay = link.get('delay', 1)
                    bw = link.get('bw', 1)
                    loss = link.get('loss', 0)

                    import math
                    if not math.isfinite(delay) or delay < 0:
                        delay = 1
                    if not math.isfinite(bw) or bw <= 0:
                        bw = 1
                    if not math.isfinite(loss) or loss < 0:
                        loss = 0

                    weight = delay * (1 + loss) / bw
                    if not math.isfinite(weight) or weight < 0:
                        weight = 1

                    self.G.add_edge(src, dst, weight=weight, controller=controller_key,
                                   delay=delay, bw=bw, loss=loss,
                                   src_port=link.get('src_port'),
                                   edge_type='switch_link')

                    if controller_id in self.G:
                        if controller_key in self.controller_to_switches:
                            if src in self.controller_to_switches[controller_key]:
                                if not self.G.has_edge(controller_id, src):
                                    self.G.add_edge(controller_id, src,
                                                  edge_type='controller_switch', weight=0.5)
                            if dst in self.controller_to_switches[controller_key]:
                                if not self.G.has_edge(controller_id, dst):
                                    self.G.add_edge(controller_id, dst,
                                                  edge_type='controller_switch', weight=0.5)

                    logger.debug(f"添加边: {src} -> {dst}, 权重: {weight}")

        for controller_key, switches in self.controller_to_switches.items():
            if isinstance(controller_key, tuple):
                ip, port = controller_key
                controller_id = f"Controller_{ip}_{port}"
            else:
                ip = controller_key
                port = 0
                controller_id = f"Controller_{ip}_{port}"

            if controller_id not in self.G:
                self.G.add_node(controller_id, node_type='controller', ip=ip, port=port)
                if root_controller_id in self.G:
                    self.G.add_edge(root_controller_id, controller_id,
                                  edge_type='controller_connection', weight=1)

            for switch_id in switches:
                if switch_id not in self.G:
                    self.G.add_node(
                        switch_id,
                        node_type='switch',
                        flow_table=self._get_switch_flow_table(switch_id)
                    )
                else:
                    if 'node_type' not in self.G.nodes[switch_id] or self.G.nodes[switch_id].get('node_type') != 'switch':
                        self.G.nodes[switch_id]['node_type'] = 'switch'
                    self.G.nodes[switch_id]['flow_table'] = self._get_switch_flow_table(switch_id)
                if not self.G.has_edge(controller_id, switch_id):
                    self.G.add_edge(controller_id, switch_id,
                                  edge_type='controller_switch', weight=0.5)

        for controller_key, hosts in self.host.items():
            if isinstance(controller_key, tuple):
                ip, port = controller_key
                controller_id = f"Controller_{ip}_{port}"
            else:
                ip = controller_key
                port = 0
                controller_id = f"Controller_{ip}_{port}"

            for host in hosts:
                dpid = host.get('dpid')
                mac = host.get('mac')
                ip = host.get('ip')

                if dpid and ip:
                    if dpid not in self.G:
                        self.G.add_node(dpid, node_type='switch')
                    else:
                        if 'node_type' not in self.G.nodes[dpid] or self.G.nodes[dpid].get('node_type') != 'switch':
                            self.G.nodes[dpid]['node_type'] = 'switch'

                    if ip not in self.G:
                        self.G.add_node(ip, node_type='host', mac=mac)
                    else:
                        if 'node_type' not in self.G.nodes[ip] or self.G.nodes[ip].get('node_type') != 'host':
                            self.G.nodes[ip]['node_type'] = 'host'
                            if mac:
                                self.G.nodes[ip]['mac'] = mac

                    self.G.add_edge(ip, dpid, weight=1, controller=controller_key,
                                  edge_type='host_switch')
                    self.G.add_edge(dpid, ip, weight=1, controller=controller_key,
                                  edge_type='host_switch')

                    logger.debug(f"添加主机连接: {mac} <-> {dpid}, IP: {ip}")

        logger.info(f"更新网络图完成: {len(self.G.nodes)} 个节点, {len(self.G.edges)} 条边")
        self.web_state.mark_topology_dirty()

    def _lookup_host_mac(self, ip):
        for hosts in self.host.values():
            for host in hosts:
                if host.get('ip') == ip:
                    return host.get('mac')
        node_data = self.G.nodes.get(ip, {}) if ip in self.G else {}
        return node_data.get('mac')

    def _controllers_for_path(self, path):
        path_switches = {node for node in path if isinstance(node, int)}
        targets = set()
        with self.client_lock:
            connected = set(self.clients.keys())
        for controller_key, switches in self.controller_to_switches.items():
            if controller_key in connected and path_switches.intersection(set(switches or [])):
                targets.add(controller_key)
        return targets

    def handle_path_install_ack(self, client_addr, message):
        path_id = message.get('path_id')
        if not path_id:
            return
        if message.get('barriers_ok') is False:
            logger.warning("[Path] path install ACK reported barrier failure: path_id=%s controller=%s",
                           path_id, client_addr)
        with self.path_install_cond:
            pending = self.pending_path_installs.get(path_id)
            if not pending:
                return
            pending['acks'].discard(client_addr)
            self.path_install_cond.notify_all()

    def _cleanup_expired_portdata_queries(self):
        now = time.time()
        expired = [rid for rid, (_, qt) in self.portdata_query_requests.items() if now - qt > 60]
        for rid in expired:
            del self.portdata_query_requests[rid]
        if expired:
            logger.info("[PortData] TTL cleanup removed %d expired queries", len(expired))

    def _cleanup_expired_link_downs(self):
        now = time.time()
        expired = [(s, d) for (s, d), ts in self.link_down_set.items() if now - ts > self.LINK_DOWN_TTL]
        for edge in expired:
            self.link_down_set.pop(edge, None)
        if expired:
            logger.info("[LinkDown] TTL cleanup removed %d expired entries", len(expired))

    def handle_host_update(self, client_addr, message):
        controller_key = client_addr if isinstance(client_addr, tuple) else (client_addr, 0)
        host = message.get('host')
        if not host:
            return
        self.host.setdefault(controller_key, [])
        if not any(h.get('mac') == host.get('mac') or h.get('ip') == host.get('ip')
                   for h in self.host[controller_key]):
            self.host[controller_key].append(host)
            self.update_graph()
        relay_msg = {'type': 'host_update', 'host': host}
        for addr in list(self.clients.keys()):
            if addr != client_addr:
                self._send_to_controller(addr, relay_msg)

    def handle_link_down(self, client_addr, message):
        src = message.get('src')
        dst = message.get('dst')
        if src is None or dst is None:
            logger.warning("link_down missing src/dst: %s", message)
            return
        now = time.time()
        existing = self.link_down_set.get((src, dst))
        if existing is not None and now - existing < 30:
            return
        self._cleanup_expired_link_downs()
        self.link_down_set[(src, dst)] = now
        self.link_down_set[(dst, src)] = now
        self.update_graph()

    def handle_link_up(self, client_addr, message):
        src = message.get('src')
        dst = message.get('dst')
        if src is None or dst is None:
            return
        self.link_down_set.pop((src, dst), None)
        self.link_down_set.pop((dst, src), None)
        self.update_graph()

    def _connect_path_service(self):
        try:
            if self.path_service_sock:
                try:
                    self.path_service_sock.close()
                except Exception:
                    pass
            self.path_service_sock = socket.socket(socket.AF_INET, socket.SOCK_STREAM)
            self.path_service_sock.settimeout(10)
            self.path_service_sock.connect((PATH_SERVICE_HOST, PATH_SERVICE_PORT))
            logger.info("[DRL] connected to path_service %s:%s", PATH_SERVICE_HOST, PATH_SERVICE_PORT)
        except Exception as exc:
            logger.warning("[DRL] path_service unavailable: %s; Dijkstra fallback will be used", exc)
            self.path_service_sock = None

    def _normalize_drl_decision(self, response, src_ip, dst_ip):
        if not response or not response.get('path'):
            return None
        full_path = [src_ip] + response['path'] + [dst_ip]
        valid, reason = validate_switch_path(self.G, full_path)
        if not valid:
            logger.warning("[DRL] invalid path from path_service (%s): %s", reason, full_path)
            return None
        return {
            'path': full_path,
            'decision_source': response.get('decision_source', 'path_service_unknown'),
            'model_used': bool(response.get('model_used', False)),
            'fallback_reason': response.get('fallback_reason'),
            'confidence': response.get('confidence'),
            'compute_time': response.get('compute_time'),
            'candidate_count': response.get('candidate_count'),
        }

    def _choose_final_path_response(self, message, drl_response, fallback_response, route_mode):
        if route_mode == 'spf':
            return fallback_response

        if route_mode == 'shadow':
            if fallback_response and fallback_response.get('status') == 'ok':
                fallback_response['path_source'] = 'shadow_fallback'
                fallback_response['decision_source'] = 'shadow_fallback'
                fallback_response['drl_shadow'] = {
                    'path': drl_response.get('path') if drl_response else None,
                    'decision_source': drl_response.get('decision_source') if drl_response else None,
                    'model_used': drl_response.get('model_used') if drl_response else False,
                    'fallback_reason': (
                        drl_response.get('fallback_reason')
                        if drl_response else 'no_drl_response'
                    ),
                    'model_confidence': drl_response.get('model_confidence') if drl_response else None,
                    'drl_compute_time': drl_response.get('drl_compute_time') if drl_response else None,
                }
            return fallback_response

        if route_mode == 'hybrid' and drl_response:
            return drl_response

        if route_mode == 'drl':
            return drl_response or {
                'status': 'error',
                'message': 'DRL route mode requested but no valid DRL path',
            }

        return fallback_response

    def _request_path_from_drl(self, message):
        src_ip = message.get('src')
        dst_ip = message.get('dst')
        route_policy = message.get('route_policy', 'shortest_path')
        try:
            src_dpid = None
            dst_dpid = None
            if src_ip in self.G:
                for node in self.G.neighbors(src_ip):
                    if isinstance(node, int):
                        src_dpid = node
                        break
            if dst_ip in self.G:
                for node in self.G.neighbors(dst_ip):
                    if isinstance(node, int):
                        dst_dpid = node
                        break
            if src_dpid is None or dst_dpid is None:
                logger.warning(
                    "[DRL] skip path_service: missing endpoint switch src=%s src_dpid=%s dst=%s dst_dpid=%s",
                    src_ip, src_dpid, dst_ip, dst_dpid
                )
                return None
            candidates = build_k_shortest_candidates(
                self.G,
                src_ip,
                dst_ip,
                k=DRL_K_CANDIDATES,
                link_down_set=self.link_down_set,
                route_policy=route_policy,
            )

            request = {
                'type': 'path_request',
                'src_node': src_dpid,
                'dst_node': dst_dpid,
                'topo_edges': build_topo_edges_for_path_service(
                    self.G, self.link_down_set, route_policy),
                'candidates': candidates,
                'route_mode': message.get('route_mode', self.route_mode),
                'route_policy': route_policy,
                'task_type': message.get('task_type', 'default'),
                'request_id': "%d-%d-%d" % (src_dpid, dst_dpid, int(time.time() * 1000)),
            }
            flow_profile = get_gart_flow_profile(request['task_type'])
            request.update({
                'flow_type': message.get('flow_type', flow_profile['flow_type']),
                'deadline_ms': float(message.get('deadline_ms', flow_profile['deadline_ms'])),
                'demand': float(message.get('demand', message.get('required_throughput', 100.0))),
            })
            logger.info(
                "[DRL] request_path route_mode=%s src=%s(%s) dst=%s(%s) task=%s policy=%s candidates=%d",
                request['route_mode'], src_ip, src_dpid, dst_ip, dst_dpid,
                request['task_type'], route_policy, len(candidates)
            )
            with self.path_service_lock:
                if self.path_service_sock is None:
                    self._connect_path_service()
                if self.path_service_sock is None:
                    return None
                try:
                    self.path_service_sock.sendall((json.dumps(request) + '\n').encode('utf-8'))
                    response_data = b''
                    while b'\n' not in response_data:
                        chunk = self.path_service_sock.recv(4096)
                        if not chunk:
                            raise ConnectionError("path_service disconnected")
                        response_data += chunk
                    line = response_data.split(b'\n', 1)[0]
                    response = json.loads(line.decode('utf-8'))
                except (socket.timeout, ConnectionError, json.JSONDecodeError) as exc:
                    logger.warning("[DRL] path_service request failed: %s", exc)
                    self._connect_path_service()
                    return None

            if response.get('status') == 'ok' and response.get('path'):
                logger.info(
                    "[DRL] path_service response decision_source=%s model_used=%s fallback_reason=%s path=%s candidates=%s compute_time=%s",
                    response.get('decision_source'), response.get('model_used'),
                    response.get('fallback_reason'), response.get('path'),
                    response.get('candidate_count'), response.get('compute_time')
                )
                return self._normalize_drl_decision(response, src_ip, dst_ip)
        except Exception as exc:
            logger.debug("[DRL] path_service call failed: %s", exc)
        return None

    def handle_path_request(self, message):
        """Handle controller path requests with DRL first and Dijkstra fallback."""
        src = message.get('src')
        dst = message.get('dst')
        if not src or not dst:
            return {'status': 'error', 'message': 'path request missing src or dst'}
        if src not in self.G or dst not in self.G:
            return {'status': 'error', 'message': 'src or dst not in graph'}

        route_mode = message.get('route_mode', self.route_mode)
        if route_mode not in {'spf', 'shadow', 'hybrid', 'drl'}:
            route_mode = self.route_mode

        drl_response = None
        if route_mode != 'spf':
            drl_decision = self._request_path_from_drl(message)
        else:
            drl_decision = None

        if drl_decision:
            drl_path = drl_decision['path']
            drl_response = {
                'status': 'ok',
                'path': drl_path,
                'src_ip': src,
                'dst_ip': dst,
                'src_mac': self._lookup_host_mac(src),
                'dst_mac': self._lookup_host_mac(dst),
                'switch_id': message.get('switch_id'),
                'in_port': message.get('in_port'),
                'task_type': message.get('task_type', 'default'),
                'route_policy': message.get('route_policy', 'shortest_path'),
                'path_source': drl_decision.get('decision_source', 'path_service_unknown'),
                'decision_source': drl_decision.get('decision_source', 'path_service_unknown'),
                'model_used': drl_decision.get('model_used', False),
                'fallback_reason': drl_decision.get('fallback_reason'),
                'model_confidence': drl_decision.get('confidence'),
                'drl_compute_time': drl_decision.get('compute_time'),
                'candidate_count': drl_decision.get('candidate_count'),
                'hop_ports': build_hop_ports(self.G, drl_path),
            }
            if 'l4_match' in message:
                drl_response['l4_match'] = message['l4_match']
            if 'session_id' in message:
                drl_response['session_id'] = message.get('session_id')

        fallback_response = None
        if route_mode in {'spf', 'shadow'} or drl_response is None:
            fallback_response = handle_path_request_with_policy(self.G, message, self.link_down_set)

        response = self._choose_final_path_response(
            message, drl_response, fallback_response, route_mode)
        if response and response.get('status') == 'ok':
            response['src_mac'] = self._lookup_host_mac(src)
            response['dst_mac'] = self._lookup_host_mac(dst)
        return response

    def stop(self):
        self.is_running = False

        for client_addr, (client_sock, _) in list(self.clients.items()):
            try:
                client_sock.close()
                logger.info(f"关闭客户端连接: {client_addr}")
                print(f"关闭客户端连接: {client_addr}")
            except:
                pass

        self.clients.clear()

        if self.sock:
            try:
                self.sock.close()
            except:
                pass

        if self.path_service_sock:
            try:
                self.path_service_sock.close()
            except:
                pass

        logger.info("服务器已停止")
        print("服务器已停止")

    def print_topo_info_loop(self):
        """Periodically emit a compact topology summary for operations."""
        logger.info("topology summary thread started")

        while True:
            try:
                switch_count = sum(len(switches) for switches in self.controller_to_switches.values())
                link_count = sum(len(links) for links in self.topo.values())
                host_count = sum(len(hosts) for hosts in self.host.values())
                logger.debug(
                    "topology summary controllers=%s switches=%s links=%s hosts=%s graph_nodes=%s graph_edges=%s",
                    len(self.clients),
                    switch_count,
                    link_count,
                    host_count,
                    len(self.G.nodes),
                    len(self.G.edges),
                )
            except Exception as e:
                logger.error("topology summary failed: %s", e)

            time.sleep(10)


def main(argv=None):
    global server_agent
    route_mode = parse_route_mode_arg(argv)

    server_agent = ServerAgent(CONTROLLER_IP, CONTROLLER_PORT, route_mode=route_mode)
    logger.info("DRL route mode: %s", route_mode)

    def signal_handler(sig, frame):
        print("\n接收到中断信号，正在关闭服务器...")
        server_agent.stop()
        sys.exit(0)

    signal.signal(signal.SIGINT, signal_handler)
    signal.signal(signal.SIGTERM, signal_handler)

    server_agent.start()

if __name__ == "__main__":
    main()
