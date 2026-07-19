from pathlib import Path

from testbed.hybrid_external_interface import (
    add_hardware_interface,
    restore_network_config,
)


ROOT = Path(__file__).resolve().parents[1]


def test_add_hardware_interface_sets_requested_ofport_in_add_port_command():
    commands = []

    def runner(command):
        commands.append(command)
        if command[:2] == ["ifconfig", "eno1"]:
            return ""
        if command[:4] == ["ip", "-o", "-4", "addr"]:
            return "2: eno1    inet 192.0.2.10/24 brd 192.0.2.255 scope global eno1\n"
        if command[:4] == ["ip", "route", "show", "default"]:
            return "default via 192.0.2.1 dev eno1 proto dhcp metric 100\n"
        if command[:3] == ["ovs-vsctl", "get", "Interface"]:
            return "20\n"
        return ""

    state = add_hardware_interface(
        intf_name="eno1",
        switch_name="s1",
        external_port=20,
        run_cmd=runner,
    )

    assert state.interface == "eno1"
    assert state.switch == "s1"
    assert state.ip_cidr == "192.0.2.10/24"
    assert state.gateway == "192.0.2.1"
    assert [
        "ovs-vsctl",
        "add-port",
        "s1",
        "eno1",
        "--",
        "set",
        "Interface",
        "eno1",
        "ofport_request=20",
    ] in commands
    assert ["ip", "addr", "flush", "dev", "eno1"] in commands


def test_restore_network_config_deletes_port_and_restores_ip_and_gateway():
    commands = []

    def runner(command):
        commands.append(command)
        return ""

    restore_network_config(
        state={
            "interface": "eno1",
            "switch": "s1",
            "ip_cidr": "192.0.2.10/24",
            "gateway": "192.0.2.1",
        },
        run_cmd=runner,
    )

    assert ["ovs-vsctl", "--if-exists", "del-port", "s1", "eno1"] in commands
    assert ["ip", "link", "set", "eno1", "up"] in commands
    assert ["ip", "addr", "add", "192.0.2.10/24", "dev", "eno1"] in commands
    assert ["ip", "route", "replace", "default", "via", "192.0.2.1", "dev", "eno1"] in commands


def test_topology_launcher_accepts_optional_external_interface_argument():
    text = (ROOT / "testbed" / "topology_launcher.py").read_text(encoding="utf-8")

    assert "external_intf" in text
    assert "add_hardware_interface" in text
    assert "restore_network_config" in text
