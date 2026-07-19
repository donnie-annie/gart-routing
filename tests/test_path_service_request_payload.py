import sys
from pathlib import Path

import networkx as nx


ROOT = Path(__file__).resolve().parents[1]
if str(ROOT) not in sys.path:
    sys.path.insert(0, str(ROOT))

from server_path_service import build_k_shortest_candidates


def test_candidate_payload_contains_switch_paths_and_metrics():
    graph = nx.DiGraph()
    graph.add_edge("h1", 1, edge_type="host_link")
    graph.add_edge(1, 2, edge_type="switch_link", delay=1, bw=10, loss=0.01)
    graph.add_edge(2, "h2", edge_type="host_link")

    candidates = build_k_shortest_candidates(graph, "h1", "h2", k=1)

    assert candidates[0]["switch_path"] == [1, 2]
    assert candidates[0]["metrics"]["delay"] == 1
    assert candidates[0]["metrics"]["min_bandwidth"] == 10
