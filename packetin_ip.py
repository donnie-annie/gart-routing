"""Host IP PacketIn routing and flow installation."""

import time

from ryu.lib.packet import ethernet, ether_types, tcp, udp
from ryu.lib.packet import in_proto as inet

from controller_helpers import l4_reverse_for_match


def handle_host_ip_packet_in(app, ev):
    """Route a host IP packet locally or through the root controller."""
    msg = ev.msg
    datapath = msg.datapath
    dpid = datapath.id
    in_port = msg.match['in_port']
    eth, pkt_type, pkt_data = ethernet.ethernet.parser(msg.data)
    src_mac = eth.src
    dst_mac = eth.dst
    if eth.ethertype == ether_types.ETH_TYPE_IP:
        ip_pkt, _next_type, payload = pkt_type.parser(pkt_data)
        src_ip = ip_pkt.src
        dst_ip = ip_pkt.dst
        sport = dport = None
        l4_fwd = None
        if ip_pkt.proto == inet.IPPROTO_TCP and payload:
            try:
                t, _, _ = tcp.tcp.parser(payload)
                sport, dport = t.src_port, t.dst_port
                l4_fwd = {'ip_proto': int(inet.IPPROTO_TCP), 'tcp_src': sport, 'tcp_dst': dport}
            except Exception:
                pass
        elif ip_pkt.proto == inet.IPPROTO_UDP and payload:
            try:
                u, _, _ = udp.udp.parser(payload)
                sport, dport = u.src_port, u.dst_port
                l4_fwd = {'ip_proto': int(inet.IPPROTO_UDP), 'udp_src': sport, 'udp_dst': dport}
            except Exception:
                pass

        task_type = app._get_task_type_by_host_ports(sport, dport)
        route_policy = app._get_policy_for_task(task_type)

        if app.ip_packet_log_enable and eth.ethertype == ether_types.ETH_TYPE_IP:
            app.logger.info("11_host_ip_packet_in_handle收到IP数据包: 源IP=%s,目标IP=%s,源MAC=%s,目标MAC=%s,交换机=%s,端口=%s",
                            src_ip, dst_ip, src_mac, dst_mac, dpid, in_port)

        if app.is_packet_capture_mode():
            app.logger.info(
                "%s capture_mode=on skip_host_ip_flow_install dpid=%s in_port=%s src_ip=%s dst_ip=%s",
                app.packet_watch_prefix, dpid, in_port, src_ip, dst_ip
            )
            return

        if app.is_link_port(dpid, in_port):
            app.logger.info("_host_ip_packet_in_handle忽略交换机链路端口的数据包: dpid=%s, in_port=%s", dpid, in_port)
            return

        dst_switch_id = None
        dst_port = None
        dst_mac_addr = None

        for sw_id in app.host_to_sw_port:
            for port in app.host_to_sw_port[sw_id]:
                for host_info in app.host_to_sw_port[sw_id][port]:
                    if host_info[1] == dst_ip:
                        dst_switch_id = sw_id
                        dst_port = port
                        dst_mac_addr = host_info[0]
                        app.logger.info("【找到】目标主机信息: 交换机=%s, 端口=%s",
                                        dst_switch_id, dst_port)
                        break
                if dst_switch_id:
                    break

        if not dst_switch_id:
            if app.is_connected:
                cache_key = (src_ip, dst_ip)
                now = time.time()
                expired = [k for k, t in app._path_requested.items() if now - t > 30]
                for key in expired:
                    app._path_requested.pop(key, None)
                    app._pending_path_packets.pop(key, None)
                if cache_key in app._path_requested and now - app._path_requested[cache_key] < 10:
                    queue = app._pending_path_packets.setdefault(cache_key, [])
                    if len(queue) < 20:
                        queue.append((datapath, msg, in_port))
                    return
                remote_hint = getattr(app, 'remote_hosts', {}).get(dst_ip)
                app.logger.info(
                    "[PathRequest] dst_not_local src=%s dst=%s src_switch=%s in_port=%s remote_hint=%s task=%s policy=%s",
                    src_ip, dst_ip, dpid, in_port, remote_hint, task_type, route_policy
                )
                app._path_requested[cache_key] = now
                app._pending_path_packets[cache_key] = [(datapath, msg, in_port)]
                app._request_path(
                    src_ip, dst_ip, dpid, in_port, msg,
                    task_type=task_type, route_policy=route_policy, l4_fwd=l4_fwd,
                )
                return
            else:
                app.logger.warning(
                    "[PathRequest] dst_not_local_but_root_disconnected src=%s dst=%s src_switch=%s",
                    src_ip, dst_ip, dpid
                )
                return

        src_switch_id = dpid

        if src_switch_id == dst_switch_id:
            app.logger.info("【处理】源主机和目标主机在同一个交换机上: dpid=%s", dpid)

            if not dst_port or not dst_mac_addr:
                return

            datapath = app.dpid_to_switch[dpid]
            p = datapath.ofproto_parser
            l4_rev = l4_reverse_for_match(l4_fwd)
            actions = [p.OFPActionSetField(eth_dst=dst_mac_addr),
                       p.OFPActionOutput(dst_port)]
            match = app._ofp_match_ip_l4(p, in_port, src_ip, dst_ip, l4_fwd)

            app.add_flow(datapath, app._get_flow_priority_for_task(task_type), match, actions)
            app.logger.info("【流表安装】正向流表: match=%s, actions=%s", match, actions)

            actions_reverse = [p.OFPActionSetField(eth_dst=src_mac),
                               p.OFPActionOutput(in_port)]
            match_reverse = app._ofp_match_ip_l4(p, dst_port, dst_ip, src_ip, l4_rev)

            app.add_flow(datapath, app._get_flow_priority_for_task(task_type), match_reverse, actions_reverse)
            app.logger.info("【流表安装】反向流表: match_reverse=%s, actions_reverse=%s", match_reverse, actions_reverse)

            app.send_packet_to_outport(datapath, msg, in_port, actions)
            app.logger.info("【成功】同一交换机流表安装完成: %s <-> %s", src_ip, dst_ip)
            return

        app.logger.info("【计算】路径: 源交换机=%s, 目标交换机=%s", src_switch_id, dst_switch_id)
        path = app.get_path(src_switch_id, dst_switch_id)

        if path and len(path) > 0:
            app.logger.info("【成功】找到路径: %s -> %s, 路径: %s", src_ip, dst_ip, path)
            app._begin_flow_tracking()
            try:
                app.install_flow_entry(path, src_ip, dst_ip, in_port, msg, task_type=task_type, l4_fwd=l4_fwd)
            finally:
                flow_records = app._end_flow_tracking()
                app._record_route_session(path, flow_records, {
                    'src_ip': src_ip,
                    'dst_ip': dst_ip,
                    'task_type': task_type,
                    'route_policy': route_policy,
                    'l4_match': l4_fwd,
                    'switch_id': dpid,
                    'in_port': in_port,
                })
        else:
            app.logger.info("【尝试】未找到最短路径，使用直接路径")
            direct_path = [src_switch_id, dst_switch_id]
            app._begin_flow_tracking()
            try:
                app.install_flow_entry(direct_path, src_ip, dst_ip, in_port, msg, task_type=task_type, l4_fwd=l4_fwd)
            finally:
                flow_records = app._end_flow_tracking()
                app._record_route_session(direct_path, flow_records, {
                    'src_ip': src_ip,
                    'dst_ip': dst_ip,
                    'task_type': task_type,
                    'route_policy': route_policy,
                    'l4_match': l4_fwd,
                    'switch_id': dpid,
                    'in_port': in_port,
                })
