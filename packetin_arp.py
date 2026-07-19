"""ARP PacketIn handling and host discovery."""

from ryu.lib.packet import arp, ethernet, ether_types, packet

from common_config import HYBRID_GATEWAY_IP, HYBRID_GATEWAY_MAC
from hybrid_gateway import is_gateway_arp_request


def _send_gateway_arp_reply(app, datapath, in_port, dst_mac, dst_ip):
    parser = datapath.ofproto_parser
    ofproto = datapath.ofproto

    reply = packet.Packet()
    reply.add_protocol(ethernet.ethernet(
        ethertype=ether_types.ETH_TYPE_ARP,
        dst=dst_mac,
        src=HYBRID_GATEWAY_MAC,
    ))
    reply.add_protocol(arp.arp(
        opcode=arp.ARP_REPLY,
        src_mac=HYBRID_GATEWAY_MAC,
        src_ip=HYBRID_GATEWAY_IP,
        dst_mac=dst_mac,
        dst_ip=dst_ip,
    ))
    reply.serialize()

    out = parser.OFPPacketOut(
        datapath=datapath,
        buffer_id=ofproto.OFP_NO_BUFFER,
        in_port=ofproto.OFPP_CONTROLLER,
        actions=[parser.OFPActionOutput(in_port)],
        data=reply.data,
    )
    datapath.send_msg(out)
    app.logger.info(
        "[HybridGateway] proxy_arp_reply gateway_ip=%s gateway_mac=%s dst_ip=%s dst_mac=%s dpid=%s in_port=%s",
        HYBRID_GATEWAY_IP, HYBRID_GATEWAY_MAC, dst_ip, dst_mac, datapath.id, in_port,
    )


def handle_switch_packet_in(app, ev):
    """Process switch-side ARP/IP learning and forwarding."""
    msg = ev.msg
    datapath = msg.datapath
    ofproto = datapath.ofproto
    parser = datapath.ofproto_parser
    dpid = datapath.id
    in_port = msg.match['in_port']
    eth, pkt_type, pkt_data = ethernet.ethernet.parser(msg.data)
    src_mac = eth.src
    dst_mac = eth.dst

    if eth.ethertype not in [ether_types.ETH_TYPE_ARP, ether_types.ETH_TYPE_IP]:
        return
    pkt, _, _ = pkt_type.parser(pkt_data)
    try:
        src_ip = pkt.src_ip
        dst_ip = pkt.dst_ip
    except Exception:
        src_ip = pkt.src
        dst_ip = pkt.dst

    if eth.ethertype == ether_types.ETH_TYPE_ARP:
        opcode = getattr(pkt, 'opcode', None)
        app.log_packet_watch(
            packet_kind='ARP',
            dpid=dpid,
            in_port=in_port,
            src_mac=src_mac,
            dst_mac=dst_mac,
            src_ip=src_ip,
            dst_ip=dst_ip,
            extra=f"opcode={opcode}",
        )
        if is_gateway_arp_request(eth.ethertype, opcode, dst_ip, HYBRID_GATEWAY_IP):
            _send_gateway_arp_reply(app, datapath, in_port, src_mac, src_ip)
            return
    elif eth.ethertype == ether_types.ETH_TYPE_IP:
        ip_proto = getattr(pkt, 'proto', None)
        app.log_packet_watch(
            packet_kind='IP',
            dpid=dpid,
            in_port=in_port,
            src_mac=src_mac,
            dst_mac=dst_mac,
            src_ip=src_ip,
            dst_ip=dst_ip,
            extra=f"ip_proto={ip_proto}",
        )

    if src_ip == "0.0.0.0":
        app.logger.info("过滤掉IP为0.0.0.0的主机: MAC=%s, 端口=%s", src_mac, in_port)
        return

    if app.is_configured_external_link_port(dpid, in_port):
        app.remember_external_host_source(src_mac, src_ip)
        if eth.ethertype == ether_types.ETH_TYPE_ARP and app.should_drop_external_arp(src_ip, dst_ip):
            app.logger.info(
                "丢弃外部未知ARP: dpid=%s, in_port=%s, src_ip=%s, dst_ip=%s, src_mac=%s",
                dpid, in_port, src_ip, dst_ip, src_mac,
            )
            return

    if eth.ethertype == ether_types.ETH_TYPE_ARP:
        opcode = getattr(pkt, 'opcode', None)
        if app._arp_dedup_should_drop(dpid, src_mac, src_ip, dst_ip, opcode):
            return

    if app.ip_packet_log_enable and eth.ethertype == ether_types.ETH_TYPE_IP:
        app.logger.info("00_switch_packet_in_handle收到数据包:源IP=%s,目标IP=%s,源MAC=%s,目标MAC=%s,交换机=%s,端口=%s",
                        src_ip, dst_ip, src_mac, dst_mac, dpid, in_port)

    app.arp_table[(dpid, src_mac, dst_ip)] = in_port
    app.mac_to_port.setdefault(dpid, {})
    app.mac_to_port[dpid].setdefault(src_mac, set())
    app.mac_to_port[dpid][src_mac].add(in_port)

    out_ports = []
    if dst_mac in app.mac_to_port[dpid]:
        out_ports = sorted(list(app.mac_to_port[dpid][dst_mac]))
        if eth.ethertype == ether_types.ETH_TYPE_IP and out_ports:
            if len(out_ports) > 1:
                app.logger.info(
                    "IP目标MAC对应多个端口，固定使用第一个端口转发: dpid=%s, dst_mac=%s, all_ports=%s, selected=%s",
                    dpid, dst_mac, out_ports, out_ports[0]
                )
            out_ports = [out_ports[0]]
        for out_port in out_ports:
            if eth.ethertype == ether_types.ETH_TYPE_ARP:
                app.logger.info("*************************ARP**************************************************")
                app.logger.info("22目标MAC地址已知,数据包类型=ARP,out_port=%s,源IP=%s,目标IP=%s,源MAC=%s,目标MAC=%s,交换机=%s,in_port=%s",
                                out_port, src_ip, dst_ip, src_mac, dst_mac, dpid, in_port)
            elif eth.ethertype == ether_types.ETH_TYPE_IP:
                app.logger.info("22目标MAC地址已知,数据包类型=IP,out_port=%s,源IP=%s,目标IP=%s,源MAC=%s,目标MAC=%s,交换机=%s,in_port=%s",
                                out_port, src_ip, dst_ip, src_mac, dst_mac, dpid, in_port)
            else:
                app.logger.info("22目标MAC地址已知,数据包类型=未知,out_port=%s,源IP=%s,目标IP=%s,源MAC=%s,目标MAC=%s,交换机=%s,in_port=%s",
                                out_port, src_ip, dst_ip, src_mac, dst_mac, dpid, in_port)
    else:
        if eth.ethertype == ether_types.ETH_TYPE_ARP:
            out_ports = app._get_loop_safe_arp_flood_ports(dpid, in_port)
            if not out_ports:
                return
            app.logger.info("*************************ARP**************************************************")
            app.logger.info("22目标MAC地址未知,数据包类型=ARP,out_ports=%s(不使用生成树),源IP=%s,目标IP=%s,源MAC=%s,目标MAC=%s,交换机=%s,in_port=%s",
                            out_ports, src_ip, dst_ip, src_mac, dst_mac, dpid, in_port)
        elif eth.ethertype == ether_types.ETH_TYPE_IP:
            return
        else:
            app.logger.info("22目标MAC地址未知,数据包类型=未知,out_port=OFPP_FLOOD,源IP=%s,目标IP=%s,源MAC=%s,目标MAC=%s,交换机=%s,in_port=%s",
                            src_ip, dst_ip, src_mac, dst_mac, dpid, in_port)

    actions1 = [parser.OFPActionOutput(p) for p in out_ports]
    actions2 = [parser.OFPActionOutput(in_port)]
    app.logger.info("交换机%s从%s号端口收到了从%s发来的%s数据包，询问%s的mac地址",
                    dpid, in_port, src_ip, eth.ethertype, dst_ip)

    if len(out_ports) == 1:
        out_port = out_ports[0]
        match1 = parser.OFPMatch(in_port=in_port, eth_dst=dst_mac, eth_src=src_mac)
        match2 = parser.OFPMatch(in_port=out_port, eth_dst=src_mac, eth_src=dst_mac)
        if app.is_packet_capture_mode():
            app.logger.info(
                "%s capture_mode=on skip_l2_shortcut_flow dpid=%s in_port=%s out_port=%s eth_type=%s",
                app.packet_watch_prefix, dpid, in_port, out_port, eth.ethertype
            )
        else:
            if msg.buffer_id != ofproto.OFP_NO_BUFFER:
                app.add_flow(datapath, 1, match1, actions1, hard_timeout=5, buffer_id=msg.buffer_id)
                app.add_flow(datapath, 1, match2, actions2, hard_timeout=5, buffer_id=msg.buffer_id)
                return
            else:
                app.add_flow(datapath, 1, match1, actions1, hard_timeout=5)
                app.add_flow(datapath, 1, match2, actions2, hard_timeout=5)
    data = None
    if msg.buffer_id == ofproto.OFP_NO_BUFFER:
        data = msg.data
    out = parser.OFPPacketOut(datapath=datapath, buffer_id=msg.buffer_id,
                              in_port=in_port, actions=actions1, data=data)
    datapath.send_msg(out)


def handle_host_arp_packet_in(app, ev):
    """Learn hosts from ARP packets received on access ports."""
    msg = ev.msg
    datapath = msg.datapath
    dpid = datapath.id
    in_port = msg.match['in_port']
    eth, pkt_type, pkt_data = ethernet.ethernet.parser(msg.data)
    src_mac = eth.src
    dst_mac = eth.dst
    if eth.ethertype == ether_types.ETH_TYPE_ARP:
        pkt, _, _ = pkt_type.parser(pkt_data)
        src_ip = pkt.src_ip
        dst_ip = pkt.dst_ip

        if src_ip == "0.0.0.0":
            app.logger.info("过滤掉IP为0.0.0.0的主机: MAC=%s, 端口=%s", src_mac, in_port)
            return

        if not app.get_port(dpid, in_port):
            return

        if app.is_link_port(dpid, in_port):
            return

        if app.should_skip_external_host_learning(src_mac, src_ip, dpid):
            app.logger.info(
                "忽略外部链路来源主机学习: MAC=%s, IP=%s, dpid=%s, in_port=%s",
                src_mac, src_ip, dpid, in_port,
            )
            return

        for link in app.topo_access_link.keys():
            if dpid == link[0] and in_port == app.topo_access_link[link][0]:
                return

        if app.host_migration_log_enable:
            app.logger.info("55555555检查主机是否已经存在于其他位置前主机信息: src_mac=%s, src_ip=%s, dpid=%s, in_port=%s",
                            src_mac, src_ip, dpid, in_port)

        app._check_host_migration(src_mac, src_ip, dpid, in_port)

        app.host_to_sw_port.setdefault(dpid, {})
        app.host_to_sw_port[dpid].setdefault(in_port, [])

        hosts = app.host_to_sw_port[dpid][in_port]
        hosts[:] = [h for h in hosts if h[0] != src_mac]
        hosts.append([src_mac, src_ip])
        app._send_to_server({
            "type": "host_update",
            "host": {
                "ip": src_ip,
                "mac": src_mac,
                "dpid": dpid,
                "port": in_port,
            }
        })
        if app.host_migration_log_enable:
            app.logger.info("主机上线/更新: MAC=%s, IP=%s, dpid=%s, in_port=%s（业务按 IP 包 L4 端口划分）",
                            src_mac, src_ip, dpid, in_port)

        if app.host_migration_log_enable:
            app.logger.info("6666666更新后的主机信息: src_mac=%s, src_ip=%s, dpid=%s, in_port=%s", src_mac, src_ip, dpid, in_port)
