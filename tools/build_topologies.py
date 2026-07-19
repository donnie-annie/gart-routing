"""Build the benchmark topology fixtures used by GART.

The generated Topology.txt format stores each physical link once. GART loads
every physical link as two directed links.
"""

from collections import deque
import json
from pathlib import Path
import random


ROOT = Path(__file__).resolve().parents[1]
TOPOLOGY_ROOT = ROOT / "topology"

NSFNET_EDGES = [
    (1, 2), (1, 3), (1, 4), (2, 3), (2, 8), (3, 6), (4, 9),
    (4, 5), (5, 6), (5, 7), (6, 13), (6, 14), (7, 8),
    (8, 11), (9, 10), (9, 12), (10, 11), (10, 13),
    (11, 12), (11, 14), (12, 13),
]

# The 23-node GEANT traffic-measurement snapshot contains 37 physical links.
# Link (6, 19) is the snapshot's lowest-capacity non-bridge edge and is excluded
# to provide a stable 36-link fixture.
GEANT2_CAPACITY_GROUPS = {
    100000: [
        (12, 22), (10, 12), (2, 12), (13, 17), (2, 4), (4, 16),
        (1, 3), (1, 7), (1, 16), (3, 10), (3, 21), (10, 16),
        (10, 17), (7, 17), (2, 7), (7, 21), (9, 16), (17, 20),
    ],
    25000: [
        (13, 19), (2, 13), (7, 19), (17, 23), (2, 23), (5, 8),
        (8, 9), (2, 18), (18, 21), (5, 16), (3, 11), (10, 11),
        (20, 22), (15, 20), (9, 15),
    ],
    1150: [(13, 14), (6, 19), (3, 14), (6, 7)],
}
GEANT2_EXCLUDED_EDGE = (6, 19)

RENATER2010_LINKS = [
    (1, 34, 1206, 155000, 0),
    (1, 35, 907, 155000, 0),
    (1, 5, 1328, 155000, 0),
    (1, 7, 923, 155000, 0),
    (1, 2, 754, 155000, 0),
    (2, 7, 660, 155000, 0),
    (3, 33, 486, 155000, 0),
    (3, 35, 832, 155000, 0),
    (3, 14, 483, 155000, 0),
    (3, 15, 353, 155000, 0),
    (4, 35, 486, 155000, 0),
    (4, 5, 624, 155000, 0),
    (5, 32, 605, 155000, 0),
    (6, 9, 345, 155000, 0),
    (6, 32, 767, 155000, 0),
    (7, 8, 863, 155000, 0),
    (8, 28, 561, 155000, 0),
    (9, 36, 860, 155000, 0),
    (10, 27, 717, 155000, 0),
    (10, 32, 418, 155000, 0),
    (10, 16, 673, 155000, 0),
    (11, 20, 252, 155000, 0),
    (11, 12, 374, 155000, 0),
    (12, 19, 239, 155000, 0),
    (13, 14, 348, 155000, 0),
    (13, 24, 364, 155000, 0),
    (16, 32, 644, 155000, 0),
    (17, 34, 457, 155000, 0),
    (17, 18, 215, 155000, 0),
    (18, 19, 278, 155000, 0),
    (20, 43, 421, 155000, 0),
    (21, 33, 631, 155000, 0),
    (21, 22, 631, 155000, 0),
    (21, 23, 631, 155000, 0),
    (23, 32, 631, 155000, 0),
    (24, 34, 361, 155000, 0),
    (25, 33, 631, 155000, 0),
    (26, 28, 1422, 155000, 0),
    (27, 28, 239, 155000, 0),
    (27, 29, 538, 155000, 0),
    (28, 32, 1206, 155000, 0),
    (28, 29, 691, 155000, 0),
    (30, 33, 631, 155000, 0),
    (31, 33, 631, 155000, 0),
    (31, 32, 631, 155000, 0),
    (32, 33, 1713, 155000, 0),
    (33, 38, 577, 155000, 0),
    (33, 39, 322, 155000, 0),
    (33, 40, 897, 155000, 0),
    (33, 41, 496, 155000, 0),
    (34, 43, 431, 155000, 0),
    (36, 37, 507, 155000, 0),
    (37, 38, 748, 155000, 0),
    (39, 40, 600, 155000, 0),
    (41, 42, 486, 155000, 0),
    (42, 43, 689, 155000, 0),
]


def _normalize_edge(edge):
    return tuple(sorted((int(edge[0]), int(edge[1]))))


def _adjacency(node_count, links):
    adjacency = {node: set() for node in range(1, node_count + 1)}
    for src, dst, *_ in links:
        adjacency[src].add(dst)
        adjacency[dst].add(src)
    return adjacency


def _validate(node_count, links, physical_link_count):
    pairs = [_normalize_edge(link) for link in links]
    if len(links) != physical_link_count or len(set(pairs)) != physical_link_count:
        raise ValueError("unexpected or duplicate physical-link count")
    if any(src == dst for src, dst in pairs):
        raise ValueError("self-links are not allowed")
    nodes = {node for pair in pairs for node in pair}
    if nodes != set(range(1, node_count + 1)):
        raise ValueError("topology node identifiers must be contiguous and 1-based")
    adjacency = _adjacency(node_count, links)
    reached = {1}
    queue = deque([1])
    while queue:
        node = queue.popleft()
        for neighbor in adjacency[node] - reached:
            reached.add(neighbor)
            queue.append(neighbor)
    if len(reached) != node_count:
        raise ValueError("topology must be connected")


def _gravity_matrix(node_count, links, seed):
    """Create a deterministic gravity-model fixture for a runnable checkout."""
    rng = random.Random(seed)
    adjacency = _adjacency(node_count, links)
    masses = [len(adjacency[node]) + 1.0 + rng.random() for node in range(1, node_count + 1)]
    products = [
        masses[src] * masses[dst]
        for src in range(node_count)
        for dst in range(node_count)
        if src != dst
    ]
    scale = 1000.0 / (sum(products) / len(products))
    values = []
    for src in range(node_count):
        for dst in range(node_count):
            values.append(0 if src == dst else max(1, round(masses[src] * masses[dst] * scale)))
    return values


def _write_dataset(name, node_count, links, metadata, tm_seed):
    physical_link_count = len(links)
    _validate(node_count, links, physical_link_count)
    directory = TOPOLOGY_ROOT / name
    directory.mkdir(parents=True, exist_ok=True)
    rows = [f"{node_count} {physical_link_count}"]
    rows.extend("%d %d %g %g %g" % tuple(link) for link in links)
    rows.append(" ".join("1" for _ in range(node_count)))
    (directory / "Topology.txt").write_text("\n".join(rows) + "\n", encoding="utf-8")
    matrix = _gravity_matrix(node_count, links, tm_seed)
    (directory / "TM.txt").write_text(" ".join(map(str, matrix)) + "\n", encoding="utf-8")
    metadata = dict(metadata)
    metadata.update({
        "name": name,
        "nodes": node_count,
        "physical_links": physical_link_count,
        "directed_links": physical_link_count * 2,
        "traffic_matrix_entries": node_count * node_count,
        "bundled_traffic_matrix": {
            "model": "deterministic gravity fixture",
            "seed": tm_seed,
            "note": "Deterministic runnable traffic fixture.",
        },
    })
    (directory / "metadata.json").write_text(
        json.dumps(metadata, indent=2, sort_keys=True) + "\n", encoding="utf-8")


def _nsfnet_links():
    return [(src, dst, 100, 10000, 0) for src, dst in NSFNET_EDGES]


def _geant2_links():
    links = []
    for capacity, edges in GEANT2_CAPACITY_GROUPS.items():
        for edge in edges:
            pair = _normalize_edge(edge)
            if pair != GEANT2_EXCLUDED_EDGE:
                links.append((pair[0], pair[1], 1000, capacity, 0))
    return sorted(links)


def _synthetic_links(node_count=300, physical_link_count=669, seed=1):
    """Build a deterministic degree-preferential connected graph."""
    rng = random.Random(seed)
    pairs = {_normalize_edge((node, node % node_count + 1)) for node in range(1, node_count + 1)}
    degree = [0] * (node_count + 1)
    for src, dst in pairs:
        degree[src] += 1
        degree[dst] += 1
    nodes = list(range(1, node_count + 1))
    while len(pairs) < physical_link_count:
        weights = [degree[node] + 1 for node in nodes]
        src = rng.choices(nodes, weights=weights, k=1)[0]
        dst = rng.choices(nodes, weights=weights, k=1)[0]
        pair = _normalize_edge((src, dst))
        if src == dst or pair in pairs:
            continue
        pairs.add(pair)
        degree[src] += 1
        degree[dst] += 1
    links = []
    for src, dst in sorted(pairs):
        delay = rng.randint(100, 2000)
        capacity = rng.choice((10000, 40000, 100000))
        links.append((src, dst, delay, capacity, 0))
    return links


def main():
    _write_dataset(
        "nsfnet", 14, _nsfnet_links(), {
            "benchmark_role": "small real-world topology",
            "expected_counts": {"nodes": 14, "directed_links": 42},
            "topology_source": (
                "https://knowledgedefinednetworking.org/data/datasets_v0/nsfnet.tar.gz"
            ),
            "edge_list_reference": (
                "https://github.com/knowledgedefinednetworking/DRL-GNN/commit/"
                "e3bc32bc6b65c1b6df570aee23bfe304fc4ebe0a"
            ),
            "traffic_matrix_source": "deterministic gravity fixture",
        }, tm_seed=1)
    _write_dataset(
        "geant2", 23, _geant2_links(), {
            "benchmark_role": "medium real-world topology",
            "expected_counts": {"nodes": 23, "directed_links": 72},
            "topology_source": (
                "https://knowledgedefinednetworking.org/data/datasets_v0/geant2.tar.gz"
            ),
            "measurement_snapshot_reference": (
                "https://github.com/GuetYe/DRL-M4MR/blob/"
                "77a3924832c0c4075aa3428883a27ea4b1d5eab5/mininet/topologies/"
                "topology-anonymised.xml"
            ),
            "normalization": {
                "source_physical_links": 37,
                "excluded_edge": list(GEANT2_EXCLUDED_EDGE),
                "reason": "The lowest-capacity non-bridge edge is omitted for a stable 36-link fixture.",
            },
            "traffic_matrix_source": "deterministic gravity fixture",
        }, tm_seed=2)
    _write_dataset(
        "renater2010", 43, RENATER2010_LINKS, {
            "benchmark_role": "medium real-world topology",
            "expected_counts": {"nodes": 43, "directed_links": 112},
            "topology_source": (
                "https://github.com/sk2/topologyzoo/blob/"
                "e278b1bdaafea5dac33883bf9c97401db4cd7347/sources/Renater2010.graphml"
            ),
            "converted_link_reference": (
                "https://github.com/ngvozdiev/tm-gen/blob/"
                "4c2fd049450b98e8993d8a336be799df3df3769f/data/topologies/"
                "Renater2010.graph"
            ),
            "traffic_matrix_source": "deterministic gravity fixture",
        }, tm_seed=3)
    synthetic_seed = 1
    synthetic_links = _synthetic_links(seed=synthetic_seed)
    _write_dataset(
        "synthetic300", 300, synthetic_links, {
            "benchmark_role": "large synthetic topology",
            "expected_counts": {
                "nodes": 300,
                "directed_links": 1338,
                "average_out_degree": 4.46,
            },
            "generator": {
                "family": "degree-preferential connected generator",
                "seed": synthetic_seed,
                "note": "Fixed instance with stable size and average out-degree.",
            },
            "traffic_matrix_source": "deterministic gravity fixture",
        }, tm_seed=4)


if __name__ == "__main__":
    main()
