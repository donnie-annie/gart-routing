#!/usr/bin/python3
"""Launch a topology from its repository Topology.txt fixture."""

import argparse
from pathlib import Path

from mininet.cli import CLI
from mininet.link import TCLink
from mininet.log import setLogLevel
from mininet.net import Mininet
from mininet.node import OVSSwitch, RemoteController

from hybrid_external_interface import add_hardware_interface, restore_network_config


PROJECT_ROOT = Path(__file__).resolve().parents[1]
EXTERNAL_SWITCH = "s1"
EXTERNAL_PORT = 20


def load_links(path):
    with open(path, "r", encoding="utf-8") as handle:
        node_count, link_count = map(int, handle.readline().split()[:2])
        links = []
        for _ in range(link_count):
            src, dst, delay, capacity, loss = handle.readline().split()[:5]
            links.append((
                int(src),
                int(dst),
                max(float(delay) * 0.01, 0.01),
                max(float(capacity) / 1000.0, 0.001),
                max(float(loss), 0.0),
            ))
    return node_count, links


def create_topology(topology_path, external_intf=None, controller_port=6654):
    node_count, links = load_links(topology_path)
    net = Mininet(controller=None, switch=OVSSwitch, link=TCLink)
    controller = net.addController(
        "c1", controller=RemoteController, ip="127.0.0.1", port=controller_port)
    switches = {
        node: net.addSwitch("s%d" % node)
        for node in range(1, node_count + 1)
    }
    for node, switch in switches.items():
        host = net.addHost("h%d" % node, ip="10.0.0.%d" % node)
        net.addLink(host, switch)
    for src, dst, delay_ms, bandwidth_mbps, loss in links:
        net.addLink(
            switches[src],
            switches[dst],
            delay="%gms" % delay_ms,
            bw=bandwidth_mbps,
            loss=loss,
        )

    external_state = None
    net.start()
    for switch in switches.values():
        switch.start([controller])
    if external_intf:
        external_state = add_hardware_interface(
            external_intf,
            switch_name=EXTERNAL_SWITCH,
            external_port=EXTERNAL_PORT,
        )
    try:
        print("Loaded topology %s: %d nodes, %d physical links"
              % (topology_path, node_count, len(links)))
        CLI(net)
    finally:
        if external_state:
            restore_network_config(external_state)
        net.stop()


def parse_args(argv=None):
    parser = argparse.ArgumentParser(description="Launch a GART topology in Mininet")
    parser.add_argument(
        "--topology",
        default=str(PROJECT_ROOT / "topology" / "nsfnet" / "Topology.txt"),
    )
    parser.add_argument("--external-intf", default=None)
    parser.add_argument("--controller-port", type=int, default=6654)
    return parser.parse_args(argv)


if __name__ == "__main__":
    setLogLevel("info")
    args = parse_args()
    create_topology(args.topology, args.external_intf, args.controller_port)
