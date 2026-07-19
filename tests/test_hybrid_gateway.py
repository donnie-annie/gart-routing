from hybrid_gateway import is_gateway_arp_request, parse_hybrid_real_routes


def test_parse_hybrid_real_routes_uses_virtual_gateway():
    routes = parse_hybrid_real_routes("192.168.103.0/24, 192.168.104.0/24")

    assert routes == ["192.168.103.0/24", "192.168.104.0/24"]


def test_gateway_arp_request_matches_only_configured_gateway():
    assert is_gateway_arp_request(
        eth_type=0x0806,
        opcode=1,
        dst_ip="10.0.0.254",
        gateway_ip="10.0.0.254",
    )
    assert not is_gateway_arp_request(
        eth_type=0x0806,
        opcode=1,
        dst_ip="192.168.103.3",
        gateway_ip="10.0.0.254",
    )
