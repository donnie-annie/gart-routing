#!/usr/bin/env python3
"""Helpers for attaching a host physical NIC to a Mininet OVS switch."""

from dataclasses import asdict, dataclass
import subprocess
from typing import Optional


@dataclass
class InterfaceState:
    interface: str
    switch: str
    ip_cidr: Optional[str] = None
    gateway: Optional[str] = None

    def to_dict(self):
        return asdict(self)


def default_run_cmd(command):
    return subprocess.check_output(command, text=True, stderr=subprocess.STDOUT)


def _first_ipv4_cidr(intf_name, run_cmd):
    output = run_cmd(["ip", "-o", "-4", "addr", "show", "dev", intf_name])
    for line in output.splitlines():
        parts = line.split()
        if "inet" in parts:
            return parts[parts.index("inet") + 1]
    return None


def _default_gateway_for(intf_name, run_cmd):
    output = run_cmd(["ip", "route", "show", "default", "dev", intf_name])
    for line in output.splitlines():
        parts = line.split()
        if "via" in parts:
            return parts[parts.index("via") + 1]
    return None


def add_hardware_interface(intf_name, switch_name="s1", external_port=20, run_cmd=default_run_cmd):
    """Attach a physical NIC to an OVS switch with a fixed OpenFlow port."""
    run_cmd(["ifconfig", intf_name])
    state = InterfaceState(
        interface=intf_name,
        switch=switch_name,
        ip_cidr=_first_ipv4_cidr(intf_name, run_cmd),
        gateway=_default_gateway_for(intf_name, run_cmd),
    )

    run_cmd(["ip", "addr", "flush", "dev", intf_name])
    run_cmd(["ip", "link", "set", intf_name, "up"])
    run_cmd([
        "ovs-vsctl",
        "add-port",
        switch_name,
        intf_name,
        "--",
        "set",
        "Interface",
        intf_name,
        f"ofport_request={int(external_port)}",
    ])

    actual_port = run_cmd(["ovs-vsctl", "get", "Interface", intf_name, "ofport"]).strip()
    if actual_port != str(int(external_port)):
        raise RuntimeError(
            f"{intf_name} attached to {switch_name} with ofport {actual_port}, "
            f"expected {external_port}"
        )
    return state


def restore_network_config(state, run_cmd=default_run_cmd):
    """Detach a physical NIC from OVS and restore its saved host networking."""
    if isinstance(state, dict):
        state = InterfaceState(**state)
    run_cmd(["ovs-vsctl", "--if-exists", "del-port", state.switch, state.interface])
    run_cmd(["ip", "link", "set", state.interface, "up"])
    if state.ip_cidr:
        run_cmd(["ip", "addr", "add", state.ip_cidr, "dev", state.interface])
    if state.gateway:
        run_cmd(["ip", "route", "replace", "default", "via", state.gateway, "dev", state.interface])
