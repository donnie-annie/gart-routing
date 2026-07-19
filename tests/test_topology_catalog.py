import json
from pathlib import Path

from gart.topologies import DEFAULT_TOPOLOGY, TOPOLOGIES, get_topology


ROOT = Path(__file__).resolve().parents[1]


EXPECTED = {
    "nsfnet": (14, 21, 42),
    "geant2": (23, 36, 72),
    "renater2010": (43, 56, 112),
    "synthetic300": (300, 669, 1338),
}


def read_fixture(name):
    directory = ROOT / "topology" / name
    lines = (directory / "Topology.txt").read_text(encoding="utf-8").splitlines()
    node_count, physical_link_count = map(int, lines[0].split()[:2])
    edges = [tuple(map(int, line.split()[:2]))
             for line in lines[1:physical_link_count + 1]]
    matrix = [float(value) for value in
              (directory / "TM.txt").read_text(encoding="utf-8").split()]
    metadata = json.loads((directory / "metadata.json").read_text(encoding="utf-8"))
    return node_count, physical_link_count, edges, matrix, metadata


def is_connected(node_count, edges):
    adjacency = {node: set() for node in range(1, node_count + 1)}
    for src, dst in edges:
        adjacency[src].add(dst)
        adjacency[dst].add(src)
    reached = {1}
    pending = [1]
    while pending:
        node = pending.pop()
        for neighbor in adjacency[node] - reached:
            reached.add(neighbor)
            pending.append(neighbor)
    return len(reached) == node_count


def test_catalog_and_fixtures_match_expected_counts():
    assert DEFAULT_TOPOLOGY == "nsfnet"
    assert set(TOPOLOGIES) == set(EXPECTED)
    for name, (expected_nodes, expected_physical, expected_directed) in EXPECTED.items():
        nodes, physical, edges, matrix, metadata = read_fixture(name)
        assert (nodes, physical, physical * 2) == (
            expected_nodes, expected_physical, expected_directed)
        assert TOPOLOGIES[name].nodes == expected_nodes
        assert TOPOLOGIES[name].directed_links == expected_directed
        assert metadata["expected_counts"]["nodes"] == expected_nodes
        assert metadata["expected_counts"]["directed_links"] == expected_directed
        assert len(matrix) == nodes * nodes


def test_fixtures_are_connected_contiguous_simple_graphs():
    for name in EXPECTED:
        nodes, physical, edges, _matrix, _metadata = read_fixture(name)
        normalized = {tuple(sorted(edge)) for edge in edges}
        assert len(edges) == physical
        assert len(normalized) == physical
        assert all(src != dst for src, dst in edges)
        assert {node for edge in edges for node in edge} == set(range(1, nodes + 1))
        assert is_connected(nodes, edges)


def test_synthetic_average_out_degree_matches_catalog():
    nodes, physical, _edges, _matrix, metadata = read_fixture("synthetic300")
    assert 2.0 * physical / nodes == 4.46
    assert metadata["expected_counts"]["average_out_degree"] == 4.46
    assert metadata["generator"]["seed"] == 1


def test_geant_normalization_is_explicit():
    _nodes, _physical, edges, _matrix, metadata = read_fixture("geant2")
    assert (6, 19) not in {tuple(sorted(edge)) for edge in edges}
    assert metadata["normalization"]["source_physical_links"] == 37
    assert metadata["normalization"]["excluded_edge"] == [6, 19]


def test_training_defaults_follow_nsfnet_catalog():
    dataset = get_topology()
    train_source = (ROOT / "gart" / "train.py").read_text(encoding="utf-8")
    assert dataset.name == "nsfnet"
    assert dataset.topology_path == ROOT / "topology" / "nsfnet" / "Topology.txt"
    assert dataset.traffic_matrix_path == ROOT / "topology" / "nsfnet" / "TM.txt"
    assert dataset.default_model_path == ROOT / "models" / "nsfnet" / "gart.pt"
    assert 'default=DEFAULT_TOPOLOGY' in train_source


def test_legacy_military_assets_are_absent():
    assert not (ROOT / "topology" / "Military").exists()
    assert not (ROOT / "models" / "GART_Military").exists()
