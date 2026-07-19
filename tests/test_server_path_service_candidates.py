import sys
from pathlib import Path

import networkx as nx


ROOT = Path(__file__).resolve().parents[1]
if str(ROOT) not in sys.path:
    sys.path.insert(0, str(ROOT))

from server_path_service import build_k_shortest_candidates


def test_build_k_shortest_candidates_returns_weighted_simple_paths():
    graph = nx.DiGraph()
    graph.add_edge("h1", 1, weight=1, edge_type="host_link")
    graph.add_edge(1, 2, weight=1, edge_type="switch_link", delay=1, bw=10, loss=0)
    graph.add_edge(2, "h2", weight=1, edge_type="host_link")
    graph.add_edge(1, 3, weight=2, edge_type="switch_link", delay=2, bw=8, loss=0)
    graph.add_edge(3, 2, weight=2, edge_type="switch_link", delay=2, bw=8, loss=0)

    candidates = build_k_shortest_candidates(graph, "h1", "h2", k=2)

    assert [item["path"] for item in candidates] == [
        ["h1", 1, 2, "h2"],
        ["h1", 1, 3, 2, "h2"],
    ]
    assert candidates[0]["path_id"] == 0
    assert candidates[0]["metrics"]["hop_count"] == 3


def test_build_k_shortest_candidates_excludes_down_links():
    graph = nx.DiGraph()
    graph.add_edge("h1", 1, weight=1, edge_type="host_link")
    graph.add_edge(1, 2, weight=1, edge_type="switch_link")
    graph.add_edge(2, "h2", weight=1, edge_type="host_link")
    graph.add_edge(1, 3, weight=1, edge_type="switch_link")
    graph.add_edge(3, 2, weight=1, edge_type="switch_link")

    candidates = build_k_shortest_candidates(graph, "h1", "h2", k=3, link_down_set={(1, 2)})

    assert candidates[0]["path"] == ["h1", 1, 3, 2, "h2"]
