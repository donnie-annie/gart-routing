"""Topology-driven per-hop training environment for the GART policy.

The production path service consumes live controller metrics.  This compact
environment provides the same observation/reward contract for reproducible
offline training from the repository topology and traffic-matrix files.
"""

import copy
import random

from .config import FLOW_PROFILES
from .observation import (
    GARTTopologyIndex,
    build_gart_observation,
    load_topology_edges,
)
from .rewards import DualReward, DualRewardConfig


class TopologyRoutingEnv:
    def __init__(self, topology_path, traffic_matrix_path=None,
                 traffic_intensity=0.7, delay_scale=0.01,
                 link_change_probability=0.02,
                 seed=1, reward_config=None, neighborhood_hops=2):
        self.random = random.Random(seed)
        self.base_edges = load_topology_edges(topology_path)
        self.node_ids = sorted({
            endpoint
            for edge in self.base_edges
            for endpoint in (edge["src"], edge["dst"])
        })
        self.traffic_intensity = max(0.0, min(float(traffic_intensity), 0.95))
        self.delay_scale = float(delay_scale)
        self.link_change_probability = max(0.0, min(float(link_change_probability), 1.0))
        self.neighborhood_hops = max(int(neighborhood_hops), 1)
        self.reward = DualReward(reward_config or DualRewardConfig())
        self.traffic_pairs = self._load_traffic_pairs(traffic_matrix_path)
        self.max_hops = max(2 * len(self.node_ids), 1)
        self.edges = []
        self.current_observation = None
        self.simulation_time = 0.0

    def _load_traffic_pairs(self, path):
        pairs = []
        if path:
            with open(path, "r", encoding="utf-8") as handle:
                values = [float(value) for value in handle.read().split()]
            expected = len(self.node_ids) ** 2
            if len(values) >= expected:
                for src_index, src in enumerate(self.node_ids):
                    for dst_index, dst in enumerate(self.node_ids):
                        weight = values[src_index * len(self.node_ids) + dst_index]
                        if src != dst and weight > 0:
                            pairs.append((src, dst, weight))
        if not pairs:
            pairs = [
                (src, dst, 1.0)
                for src in self.node_ids
                for dst in self.node_ids
                if src != dst
            ]
        return pairs

    def _sample_flow(self):
        src, dst, _ = self.random.choices(
            self.traffic_pairs,
            weights=[item[2] for item in self.traffic_pairs],
            k=1,
        )[0]
        labels = list(FLOW_PROFILES)
        flow_type = self.random.choices(
            labels,
            weights=[FLOW_PROFILES[label]["proportion"] for label in labels],
            k=1,
        )[0]
        demand_by_type = {"EU": 100.0, "MU": 1500.0, "LU": 500.0, "RT": 1500.0}
        return src, dst, flow_type, demand_by_type[flow_type]

    def _reset_link_state(self):
        self.edges = copy.deepcopy(self.base_edges)
        for edge in self.edges:
            edge["delay"] = max(float(edge["delay"]) * self.delay_scale, 0.01)
            utilization = self.traffic_intensity * self.random.uniform(0.5, 1.0)
            edge["available_bandwidth"] = edge["capacity"] * (1.0 - utilization)
            edge["enabled"] = True
        self.topology_index = GARTTopologyIndex(self.edges)

    def reset(self):
        self._reset_link_state()
        # Exponential inter-arrival times produce a Poisson flow process.
        self.simulation_time += self.random.expovariate(
            max(self.traffic_intensity, 1e-6))
        self.source, self.destination, self.flow_type, self.required_throughput = self._sample_flow()
        self.deadline_ms = FLOW_PROFILES[self.flow_type]["deadline_ms"]
        self.current = self.source
        self.visited = [self.source]
        self.path = [self.source]
        self.elapsed_ms = 0.0
        self.minimum_throughput = float("inf")
        self.success_probability = 1.0
        self.done = False
        return self._observation()

    def _observation(self):
        self.current_observation = build_gart_observation(
            self.topology_index,
            current_node=self.current,
            destination_node=self.destination,
            visited_nodes=self.visited,
            deadline_ms=self.deadline_ms,
            neighborhood_hops=self.neighborhood_hops,
        )
        return self.current_observation

    def _find_link(self, src, dst):
        for edge in self.edges:
            if edge["src"] == src and edge["dst"] == dst and edge.get("enabled", True):
                return edge
        return None

    def _update_dynamic_links(self):
        for edge in self.edges:
            if self.random.random() >= self.link_change_probability:
                continue
            factor = self.random.uniform(0.6, 1.1)
            edge["available_bandwidth"] = max(
                0.0,
                min(edge["capacity"], edge["available_bandwidth"] * factor),
            )
            # Short-lived link disruption; a later update can restore it.
            edge["enabled"] = self.random.random() > 0.05
        for node_id in self.node_ids:
            outgoing = [edge for edge in self.edges if edge["src"] == node_id]
            if outgoing and not any(edge.get("enabled", True) for edge in outgoing):
                max(outgoing, key=lambda item: item["available_bandwidth"])["enabled"] = True

    def step(self, next_node):
        if self.done:
            raise RuntimeError("step called after a terminal GART transition")
        next_node = int(next_node)
        routing_loop = next_node in self.visited
        link = self._find_link(self.current, next_node)
        ack_received = link is not None

        if routing_loop:
            local_reward = self.reward.local(routing_loop=True)
            self.done = True
        elif not ack_received:
            local_reward = self.reward.local(ack_received=False)
            self.done = True
        else:
            local_reward = self.reward.local(
                available_bandwidth=link["available_bandwidth"],
                maximum_capacity=link["capacity"],
            )
            utilization = 1.0 - min(link["available_bandwidth"] / link["capacity"], 1.0)
            self.elapsed_ms += link["delay"] * (1.0 + utilization)
            self.minimum_throughput = min(
                self.minimum_throughput, link["available_bandwidth"])
            self.success_probability *= 1.0 - link["loss"]
            link["available_bandwidth"] = max(
                0.0, link["available_bandwidth"] - self.required_throughput)
            self.current = next_node
            self.visited.append(next_node)
            self.path.append(next_node)
            self.done = (
                self.current == self.destination
                or self.elapsed_ms > self.deadline_ms
                or len(self.path) >= self.max_hops
            )

        global_reward = None
        if self.done:
            delivered = self.current == self.destination and ack_received and not routing_loop
            achieved = self.minimum_throughput if delivered and self.minimum_throughput != float("inf") else 0.0
            packet_loss = 1.0 - self.success_probability if delivered else 1.0
            actual_fct = self.elapsed_ms if self.elapsed_ms > 0 else self.deadline_ms * 2.0
            global_reward = self.reward.global_reward(
                actual_fct_ms=actual_fct,
                expected_fct_ms=self.deadline_ms,
                achieved_throughput=achieved,
                required_throughput=self.required_throughput,
                packet_loss_rate=packet_loss,
            )

        combined = self.reward.combined(
            local_reward, global_reward=global_reward, terminated=self.done)
        info = {
            "flow_type": self.flow_type,
            "deadline_ms": self.deadline_ms,
            "actual_fct_ms": self.elapsed_ms,
            "local_reward": local_reward,
            "global_reward": global_reward,
            "path": list(self.path),
            "delivered": self.done and self.current == self.destination,
            "arrival_time": self.simulation_time,
        }

        if self.done:
            next_observation = None
        else:
            self._update_dynamic_links()
            next_observation = self._observation()
        return next_observation, combined, self.done, info
