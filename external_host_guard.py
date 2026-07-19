import ipaddress


def _normalize_mac(mac):
    return (mac or "").strip().lower()


def _normalize_ip(ip):
    return (ip or "").strip()


def _external_host_key(mac, ip):
    return (_normalize_mac(mac), _normalize_ip(ip))


def remember_external_host_source(sources, mac, ip):
    key = _external_host_key(mac, ip)
    if not key[0] or not key[1] or key[1] == "0.0.0.0":
        return False
    sources.add(key)
    return True


def is_external_host_source(sources, mac, ip):
    return _external_host_key(mac, ip) in sources


def should_skip_external_host_learning(sources, mac, ip, dpid, virtual_dpid_max):
    if not is_external_host_source(sources, mac, ip):
        return False
    try:
        return int(dpid) <= int(virtual_dpid_max)
    except (TypeError, ValueError):
        return True


def purge_host_records_for_source(host_to_sw_port, mac, ip):
    key = _external_host_key(mac, ip)
    removed = []

    for dpid in list(host_to_sw_port.keys()):
        ports = host_to_sw_port.get(dpid, {})
        for port in list(ports.keys()):
            kept_hosts = []
            for host in ports.get(port, []):
                host_mac = host[0] if len(host) > 0 else None
                host_ip = host[1] if len(host) > 1 else None
                if _external_host_key(host_mac, host_ip) == key:
                    removed.append((dpid, port, host))
                else:
                    kept_hosts.append(host)
            if kept_hosts:
                ports[port] = kept_hosts
            else:
                ports.pop(port, None)
        if not ports:
            host_to_sw_port.pop(dpid, None)

    return removed


def purge_virtual_host_records_for_source(host_to_sw_port, mac, ip, virtual_dpid_max):
    key = _external_host_key(mac, ip)
    removed = []

    for dpid in list(host_to_sw_port.keys()):
        try:
            is_virtual = int(dpid) <= int(virtual_dpid_max)
        except (TypeError, ValueError):
            is_virtual = True
        if not is_virtual:
            continue

        ports = host_to_sw_port.get(dpid, {})
        for port in list(ports.keys()):
            kept_hosts = []
            for host in ports.get(port, []):
                host_mac = host[0] if len(host) > 0 else None
                host_ip = host[1] if len(host) > 1 else None
                if _external_host_key(host_mac, host_ip) == key:
                    removed.append((dpid, port, host))
                else:
                    kept_hosts.append(host)
            if kept_hosts:
                ports[port] = kept_hosts
            else:
                ports.pop(port, None)
        if not ports:
            host_to_sw_port.pop(dpid, None)

    return removed


def should_drop_external_arp(src_ip, dst_ip, allowed_prefixes):
    if _normalize_ip(src_ip) == "0.0.0.0":
        return True
    try:
        dst_address = ipaddress.ip_address(_normalize_ip(dst_ip))
    except ValueError:
        return True

    for prefix in allowed_prefixes:
        try:
            if dst_address in ipaddress.ip_network(prefix, strict=False):
                return False
        except ValueError:
            continue
    return True
