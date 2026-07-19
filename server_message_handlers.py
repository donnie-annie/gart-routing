"""Server message dispatch, heartbeat checks, and connection cleanup."""

import json
import logging
import time
import traceback


logger = logging.getLogger("server_agent")


def process_message(app, client_sock, client_addr, data):
    """Parse and dispatch one controller message."""
    with app.client_lock:
        if client_addr in app.client_last_heartbeat:
            app.client_last_heartbeat[client_addr] = time.time()

    try:
        message = json.loads(data.decode('utf-8'))
        app.new_method(client_addr, message)

        message_type = message.get('type')
        response = {'status': 'ok'}

        if message_type == 'heartbeat':
            logger.debug(f"收到客户端 {client_addr} 的心跳")
            return

        if message_type == 'disconnect':
            logger.info(f"收到客户端 {client_addr} 的主动下线消息")
            print(f"收到客户端 {client_addr} 的主动下线消息")
            app.cleanup_disconnected_client(client_addr, reason="主动下线")
            return

        if message_type == 'topo':
            app.handle_topo_message(client_addr, message)
        elif message_type == 'host':
            app.handle_host_message(client_addr, message)
        elif message_type == 'path_request':
            response = app.handle_path_request(message)
            if response.get('status') != 'ok' or 'path' not in response:
                app._send_to_controller(client_addr, response)
                return

            path_id = "%s-%s-%d" % (client_addr[0], client_addr[1], time.time_ns())
            response['type'] = 'path_response'
            response['path_id'] = path_id
            targets = app._controllers_for_path(response.get('path', []))
            non_request_targets = {addr for addr in targets if addr != client_addr}

            with app.path_install_cond:
                app.pending_path_installs[path_id] = {
                    'acks': set(non_request_targets),
                    'created': time.time(),
                }

            for addr in non_request_targets:
                app._send_to_controller(addr, response)

            deadline = time.time() + 2.0
            with app.path_install_cond:
                while app.pending_path_installs.get(path_id, {}).get('acks') and time.time() < deadline:
                    app.path_install_cond.wait(timeout=max(0.0, deadline - time.time()))
                missing = app.pending_path_installs.pop(path_id, {}).get('acks', set())

            if missing:
                logger.warning("[Path] install ACK timeout for path_id=%s, missing=%s",
                               path_id, list(missing))
            app._send_to_controller(client_addr, response)
            return
        elif message_type == 'host_update':
            app.handle_host_update(client_addr, message)
            return
        elif message_type == 'path_install_ack':
            app.handle_path_install_ack(client_addr, message)
            return
        elif message_type == 'link_down':
            app.handle_link_down(client_addr, message)
            return
        elif message_type == 'link_up':
            app.handle_link_up(client_addr, message)
            return
        elif message_type == 'flow_removed':
            app.handle_flow_removed(client_addr, message)
            return
        elif message_type == 'portdata_query':
            app.handle_portdata_query(client_addr, message)
            return
        elif message_type == 'portdata_response':
            app.handle_portdata_response(client_addr, message)
            return
        elif message_type == 'lldp_report':
            app.handle_lldp_report(client_addr, message)
            return
        else:
            logger.warning(f"未知的消息类型: {message_type}")
            print(f"未知的消息类型: {message_type}")
            response = {'status': 'error', 'message': f'Unknown message type: {message_type}'}

        out_data = json.dumps(response, ensure_ascii=False) + '\n'
        client_sock.sendall(out_data.encode('utf-8'))
    except json.JSONDecodeError as e:
        logger.error(f"JSON 解析错误: {e}")
        logger.error(f"原始数据: {data}")
        print(f"JSON 解析错误: {e}")
        error_response = {'status': 'error', 'message': f'JSON parse error: {str(e)}'}
        error_data = json.dumps(error_response) + '\n'
        client_sock.sendall(error_data.encode('utf-8'))
    except Exception as e:
        logger.error(f"处理消息时出错: {e}")
        logger.error(traceback.format_exc())
        print(f"处理消息时出错: {e}")
        error_response = {'status': 'error', 'message': f'Error processing message: {str(e)}'}
        error_data = json.dumps(error_response) + '\n'
        client_sock.sendall(error_data.encode('utf-8'))


def heartbeat_check_loop(app):
    """Remove clients that exceed the heartbeat timeout."""
    while app.is_running:
        try:
            current_time = time.time()
            disconnected_clients = []

            with app.client_lock:
                for client_addr, last_heartbeat in list(app.client_last_heartbeat.items()):
                    time_since_last_heartbeat = current_time - last_heartbeat
                    if time_since_last_heartbeat > app.heartbeat_timeout:
                        logger.warning(f"客户端 {client_addr} 心跳超时 ({time_since_last_heartbeat:.2f}秒)，认为已断联")
                        print(f"客户端 {client_addr} 心跳超时 ({time_since_last_heartbeat:.2f}秒)，认为已断联")
                        disconnected_clients.append(client_addr)

            for client_addr in disconnected_clients:
                app.cleanup_disconnected_client(client_addr, reason="心跳超时")

            app._cleanup_expired_portdata_queries()
            app._cleanup_expired_link_downs()
            time.sleep(app.heartbeat_interval)
        except Exception as e:
            logger.error(f"心跳检测循环出错: {e}")
            logger.error(traceback.format_exc())
            time.sleep(app.heartbeat_interval)


def cleanup_disconnected_client(app, client_addr, reason="未知"):
    """Remove state associated with a disconnected controller."""
    try:
        logger.info(f"清理客户端 {client_addr} 的数据，原因: {reason}")
        print(f"清理客户端 {client_addr} 的数据，原因: {reason}")

        with app.client_lock:
            if client_addr in app.clients:
                client_sock, _ = app.clients[client_addr]
                try:
                    client_sock.close()
                except Exception:
                    pass
                del app.clients[client_addr]

            if client_addr in app.client_last_heartbeat:
                del app.client_last_heartbeat[client_addr]

        if client_addr in app.topo:
            del app.topo[client_addr]
            logger.info(f"已删除客户端 {client_addr} 的链路信息")

        if client_addr in app.host:
            del app.host[client_addr]
            logger.info(f"已删除客户端 {client_addr} 的主机信息")

        disconnected_switches = set(app.controller_to_switches.get(client_addr, []))
        if disconnected_switches and hasattr(app, 'link_down_set'):
            for edge in list(app.link_down_set.keys()):
                if edge[0] in disconnected_switches or edge[1] in disconnected_switches:
                    app.link_down_set.pop(edge, None)

        if client_addr in app.controller_to_switches:
            del app.controller_to_switches[client_addr]
            logger.info(f"已删除客户端 {client_addr} 的交换机信息")

        if hasattr(app, 'controller_route_sessions') and client_addr in app.controller_route_sessions:
            del app.controller_route_sessions[client_addr]
            logger.info(f"已删除客户端 {client_addr} 的路径会话信息")

        request_ids_to_remove = []
        for request_id, (requester_addr, _) in app.portdata_query_requests.items():
            if requester_addr == client_addr:
                request_ids_to_remove.append(request_id)
        for request_id in request_ids_to_remove:
            del app.portdata_query_requests[request_id]
            logger.debug(f"清理控制器 {client_addr} 的PortData查询请求记录: request_id={request_id}")

        app.update_graph()

        logger.info(f"客户端 {client_addr} 的数据清理完成")
        print(f"客户端 {client_addr} 的数据清理完成")
    except Exception as e:
        logger.error(f"清理客户端 {client_addr} 数据时出错: {e}")
        logger.error(traceback.format_exc())
