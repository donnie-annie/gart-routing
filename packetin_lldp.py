"""LLDP parsing, delay reporting, and inter-domain link updates."""

import time

from ryu.lib.packet import ethernet, ether_types
from ryu.topology.switches import LLDPPacket
from ryu.base.app_manager import lookup_service_brick


def parse_lldp_source(data):
    parsed = LLDPPacket.lldp_parse(data)
    if len(parsed) < 2:
        raise LLDPPacket.LLDPUnknownFormat()
    return parsed[0], parsed[1]


def handle_lldp_packet_in(app, ev):
    """Process one LLDP PacketIn event."""
    try:
        msg = ev.msg
        datapath = msg.datapath

        if not msg.data or len(msg.data) == 0:
            return

        eth, pkt_type, pkt_data = ethernet.ethernet.parser(msg.data)
        dpid = datapath.id
        port = msg.match['in_port']

        if eth.ethertype == ether_types.ETH_TYPE_LLDP:
            try:
                src_dpid, src_port_no = parse_lldp_source(msg.data)
                dst_dpid = dpid
                dst_inport = port

                if src_dpid == dst_dpid:
                    return
                if port >= datapath.ofproto.OFPP_MAX:
                    return

                now_time = time.time()

                if app.switches is None:
                    app.switches = lookup_service_brick("switches")

                timestamp = None
                echodelay = 0.0

                if app.switches is not None:
                    for port_obj in app.switches.ports.keys():
                        if src_dpid == port_obj.dpid and src_port_no == port_obj.port_no:
                            port_data = app.switches.ports[port_obj]
                            timestamp = port_data.timestamp
                            echodelay = getattr(port_data, 'echo_delay', 0.0)
                            break

                if timestamp is not None:
                    app._send_lldp_report_to_server(
                        src_dpid=src_dpid,
                        src_port_no=src_port_no,
                        dst_dpid=dst_dpid,
                        dst_inport=dst_inport,
                        send_time=timestamp,
                        echodelay_src=echodelay,
                        receive_time=now_time
                    )
                else:
                    app.logger.debug(
                        "LLDP源端口时间戳缺失，跳过上报: src_dpid=%s, src_port=%s, dst_dpid=%s, dst_inport=%s",
                        src_dpid, src_port_no, dst_dpid, dst_inport
                    )

                if src_dpid not in app.dpid_to_switch.keys():
                    if (dpid, src_dpid) in app.topo_inter_link or (src_dpid, dpid) in app.topo_inter_link:
                        pass
                    elif (dpid, src_dpid) not in app.topo_access_link:
                        app.topo_access_link[(dpid, src_dpid)] = [port, now_time, 0, 0, 0]
                        app._mark_permanent_link_port(dpid, port)
                        app.graph.add_edge(dpid, src_dpid)
                    else:
                        app.topo_access_link[(dpid, src_dpid)][1] = now_time
                        app._mark_permanent_link_port(dpid, port)
            except LLDPPacket.LLDPUnknownFormat:
                return
            except Exception:
                app.logger.exception("处理LLDP数据包时发生异常: dpid=%s, port=%s", dpid, port)
                return
    except Exception:
        app.logger.exception("_lldp_packet_in_handle 处理数据包时发生异常")
        return
