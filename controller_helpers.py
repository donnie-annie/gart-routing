"""Reusable controller helpers for ARP flooding and reverse L4 matches."""

from ryu.ofproto import ofproto_v1_3


def get_loop_safe_arp_flood_ports(
    dpid,
    in_port,
    switch_mac_to_port,
    topo_inter_link,
    topo_access_link,
    is_link_port_fn,
    get_port_from_link_fn,
):
    """Return valid ARP flood ports except the ingress port."""
    all_ports = list(switch_mac_to_port.get(dpid, {}).keys())
    candidate_ports = []
    for p in all_ports:
        if p == in_port:
            continue
        if p >= ofproto_v1_3.OFPP_MAX:
            continue
        candidate_ports.append(p)
    return sorted(candidate_ports)


def l4_reverse_for_match(l4_fwd):
    """Swap TCP or UDP endpoints for the reverse flow match."""
    if not l4_fwd:
        return None
    rev = {'ip_proto': l4_fwd['ip_proto']}
    if 'tcp_src' in l4_fwd:
        rev['tcp_src'] = l4_fwd['tcp_dst']
        rev['tcp_dst'] = l4_fwd['tcp_src']
        return rev
    if 'udp_src' in l4_fwd:
        rev['udp_src'] = l4_fwd['udp_dst']
        rev['udp_dst'] = l4_fwd['udp_src']
        return rev
    return None
