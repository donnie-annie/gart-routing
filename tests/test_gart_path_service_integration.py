import importlib.util
from pathlib import Path

import networkx as nx

from server_path_service import build_topo_edges_for_path_service


ROOT = Path(__file__).resolve().parents[1]
PATH_SERVICE = ROOT / "gart" / "path_service.py"


def load_path_service_module():
    spec = importlib.util.spec_from_file_location(
        "gart_path_service_under_test", PATH_SERVICE)
    module = importlib.util.module_from_spec(spec)
    spec.loader.exec_module(module)
    return module


def test_controller_exports_gart_dynamic_link_features():
    graph = nx.DiGraph()
    graph.add_edge(
        1,
        2,
        bw=100.0,
        utilization=0.25,
        delay=3.0,
        loss=0.02,
        status="up",
    )

    edges = build_topo_edges_for_path_service(graph)

    assert edges == [{
        "src": 1,
        "dst": 2,
        "weight": 1.0,
        "capacity": 100.0,
        "available_bandwidth": 75.0,
        "delay": 3.0,
        "loss": 0.02,
        "utilization": 0.25,
        "status": "up",
    }]


def test_gart_mode_without_checkpoint_has_safe_dijkstra_fallback():
    module = load_path_service_module()
    service = module.GARTPathService.__new__(module.GARTPathService)
    service.model_kind = "gart"
    service.gart_model = None
    service._static_topology_edges = []

    decision = service.compute_path(
        1,
        3,
        topo_edges=[
            {"src": 1, "dst": 2, "weight": 1},
            {"src": 2, "dst": 3, "weight": 1},
            {"src": 1, "dst": 3, "weight": 5},
        ],
        flow={"deadline_ms": 20.0},
    )

    assert decision["path"] == [1, 2, 3]
    assert decision["decision_source"] == "dijkstra"
    assert decision["model_used"] is False
    assert decision["fallback_reason"] == "gart_model_not_loaded"
