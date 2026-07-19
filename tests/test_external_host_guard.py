from external_host_guard import (
    is_external_host_source,
    purge_host_records_for_source,
    purge_virtual_host_records_for_source,
    remember_external_host_source,
    should_skip_external_host_learning,
    should_drop_external_arp,
)


def test_remembered_external_host_source_matches_mac_and_ip():
    sources = set()

    remember_external_host_source(sources, "AA:BB:CC:00:00:01", "10.5.0.13")

    assert is_external_host_source(sources, "aa:bb:cc:00:00:01", "10.5.0.13")
    assert not is_external_host_source(sources, "aa:bb:cc:00:00:01", "10.5.0.14")


def test_purge_host_records_for_external_source_removes_only_that_host():
    host_to_sw_port = {
        28: {
            5: [["f4:84:8d:99:42:72", "10.5.0.13"], ["aa:aa:aa:aa:aa:aa", "10.0.0.28"]],
            6: [["f4:84:8d:99:42:72", "10.5.0.13"]],
        },
        31: {
            2: [["bb:bb:bb:bb:bb:bb", "10.0.0.31"]],
        },
    }

    removed = purge_host_records_for_source(host_to_sw_port, "F4:84:8D:99:42:72", "10.5.0.13")

    assert removed == [
        (28, 5, ["f4:84:8d:99:42:72", "10.5.0.13"]),
        (28, 6, ["f4:84:8d:99:42:72", "10.5.0.13"]),
    ]
    assert host_to_sw_port == {
        28: {
            5: [["aa:aa:aa:aa:aa:aa", "10.0.0.28"]],
        },
        31: {
            2: [["bb:bb:bb:bb:bb:bb", "10.0.0.31"]],
        },
    }


def test_external_arp_to_real_management_subnet_is_dropped():
    assert should_drop_external_arp("10.5.0.13", "10.5.1.201", ["10.0.0.0/24"])


def test_external_arp_to_virtual_mininet_subnet_is_allowed():
    assert not should_drop_external_arp("10.5.0.13", "10.0.0.28", ["10.0.0.0/24"])


def test_external_source_is_only_blocked_on_virtual_dpids():
    sources = set()
    mac = "1c:87:2c:64:2f:56"
    ip = "192.168.103.3"

    remember_external_host_source(sources, mac, ip)

    assert should_skip_external_host_learning(sources, mac, ip, dpid=28, virtual_dpid_max=1000)
    assert not should_skip_external_host_learning(
        sources, mac, ip, dpid=128986965761, virtual_dpid_max=1000
    )


def test_virtual_purge_keeps_real_switch_host_location():
    host_to_sw_port = {
        28: {
            5: [["1c:87:2c:64:2f:56", "192.168.103.3"]],
        },
        128986965761: {
            3: [["1c:87:2c:64:2f:56", "192.168.103.3"]],
        },
    }

    removed = purge_virtual_host_records_for_source(
        host_to_sw_port,
        "1c:87:2c:64:2f:56",
        "192.168.103.3",
        virtual_dpid_max=1000,
    )

    assert removed == [(28, 5, ["1c:87:2c:64:2f:56", "192.168.103.3"])]
    assert host_to_sw_port == {
        128986965761: {
            3: [["1c:87:2c:64:2f:56", "192.168.103.3"]],
        },
    }
