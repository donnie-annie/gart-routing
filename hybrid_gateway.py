import ipaddress


ARP_REQUEST = 1
ETH_TYPE_ARP = 0x0806


def parse_hybrid_real_routes(raw_value):
    routes = []
    for item in (raw_value or "").split(","):
        item = item.strip()
        if not item:
            continue
        try:
            routes.append(str(ipaddress.ip_network(item, strict=False)))
        except ValueError:
            continue
    return routes


def is_gateway_arp_request(eth_type, opcode, dst_ip, gateway_ip):
    return (
        int(eth_type) == ETH_TYPE_ARP
        and int(opcode) == ARP_REQUEST
        and str(dst_ip) == str(gateway_ip)
    )
