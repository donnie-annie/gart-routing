import importlib
import sys
import types


def load_packetin_lldp(monkeypatch):
    ryu = types.ModuleType("ryu")
    ryu_lib = types.ModuleType("ryu.lib")
    ryu_packet = types.ModuleType("ryu.lib.packet")
    ethernet_module = types.ModuleType("ryu.lib.packet.ethernet")
    ether_types_module = types.ModuleType("ryu.lib.packet.ether_types")
    ryu_topology = types.ModuleType("ryu.topology")
    switches_module = types.ModuleType("ryu.topology.switches")
    ryu_base = types.ModuleType("ryu.base")
    app_manager_module = types.ModuleType("ryu.base.app_manager")

    class FakeLLDPPacket:
        class LLDPUnknownFormat(Exception):
            pass

        @staticmethod
        def lldp_parse(data):
            return (1, 1)

    switches_module.LLDPPacket = FakeLLDPPacket
    app_manager_module.lookup_service_brick = lambda name: None

    monkeypatch.setitem(sys.modules, "ryu", ryu)
    monkeypatch.setitem(sys.modules, "ryu.lib", ryu_lib)
    monkeypatch.setitem(sys.modules, "ryu.lib.packet", ryu_packet)
    monkeypatch.setitem(sys.modules, "ryu.lib.packet.ethernet", ethernet_module)
    monkeypatch.setitem(sys.modules, "ryu.lib.packet.ether_types", ether_types_module)
    monkeypatch.setitem(sys.modules, "ryu.topology", ryu_topology)
    monkeypatch.setitem(sys.modules, "ryu.topology.switches", switches_module)
    monkeypatch.setitem(sys.modules, "ryu.base", ryu_base)
    monkeypatch.setitem(sys.modules, "ryu.base.app_manager", app_manager_module)
    sys.modules.pop("packetin_lldp", None)
    return importlib.import_module("packetin_lldp")


def test_parse_lldp_source_accepts_extra_values(monkeypatch):
    packetin_lldp = load_packetin_lldp(monkeypatch)
    monkeypatch.setattr(
        packetin_lldp.LLDPPacket,
        "lldp_parse",
        lambda data: (128985343745, 21, "ttl-extra"),
    )

    assert packetin_lldp.parse_lldp_source(b"packet") == (128985343745, 21)


def test_parse_lldp_source_accepts_two_values(monkeypatch):
    packetin_lldp = load_packetin_lldp(monkeypatch)
    monkeypatch.setattr(
        packetin_lldp.LLDPPacket,
        "lldp_parse",
        lambda data: (1, 20),
    )

    assert packetin_lldp.parse_lldp_source(b"packet") == (1, 20)
