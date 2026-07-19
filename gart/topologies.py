"""Topology catalog and path resolution helpers."""

from dataclasses import dataclass
from pathlib import Path


PROJECT_ROOT = Path(__file__).resolve().parents[1]
DEFAULT_TOPOLOGY = "nsfnet"


@dataclass(frozen=True)
class TopologySpec:
    name: str
    nodes: int
    directed_links: int

    @property
    def directory(self):
        return PROJECT_ROOT / "topology" / self.name

    @property
    def topology_path(self):
        return self.directory / "Topology.txt"

    @property
    def traffic_matrix_path(self):
        return self.directory / "TM.txt"

    @property
    def default_model_path(self):
        return PROJECT_ROOT / "models" / self.name / "gart.pt"


TOPOLOGIES = {
    item.name: item
    for item in (
        TopologySpec("nsfnet", 14, 42),
        TopologySpec("geant2", 23, 72),
        TopologySpec("renater2010", 43, 112),
        TopologySpec("synthetic300", 300, 1338),
    )
}


def get_topology(name=DEFAULT_TOPOLOGY):
    key = (name or DEFAULT_TOPOLOGY).strip().lower()
    try:
        return TOPOLOGIES[key]
    except KeyError as exc:
        choices = ", ".join(TOPOLOGIES)
        raise ValueError("unknown topology %r; choose one of: %s" % (name, choices)) from exc
