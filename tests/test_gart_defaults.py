import math
from pathlib import Path
import sys
import tempfile
import unittest


ROOT = Path(__file__).resolve().parents[1]
if str(ROOT) not in sys.path:
    sys.path.insert(0, str(ROOT))

from gart.config import FLOW_PROFILES, GARTConfig
from gart.observation import build_gart_observation
from gart.rewards import DualReward
from gart.topology_env import TopologyRoutingEnv


class GARTDefaultsTests(unittest.TestCase):
    def test_flow_profiles(self):
        self.assertEqual(FLOW_PROFILES["EU"], {
            "proportion": 0.05, "deadline_ms": 20.0})
        self.assertEqual(FLOW_PROFILES["MU"]["deadline_ms"], 50.0)
        self.assertEqual(FLOW_PROFILES["LU"]["proportion"], 0.70)
        self.assertEqual(FLOW_PROFILES["RT"]["deadline_ms"], 200.0)
        self.assertTrue(math.isclose(
            sum(item["proportion"] for item in FLOW_PROFILES.values()), 1.0))

    def test_model_and_ppo_defaults(self):
        config = GARTConfig()
        self.assertEqual(config.gat_layers, 2)
        self.assertEqual(config.attention_heads, 4)
        self.assertEqual(config.embedding_dim_per_head, 16)
        self.assertEqual(config.embedding_dim, 64)
        self.assertEqual(config.actor_hidden, (64, 64))
        self.assertEqual(config.critic_hidden, (64, 64))
        self.assertEqual(config.learning_rate, 1e-5)
        self.assertEqual(config.discount_factor, 0.99)
        self.assertEqual(config.gae_lambda, 0.95)
        self.assertEqual(config.ppo_clip, 0.1)
        self.assertEqual(config.ppo_epochs, 10)
        self.assertEqual(config.rollout_length, 2048)
        self.assertEqual(config.mini_batch_size, 64)
        self.assertEqual(config.local_reward_weight, 0.5)
        self.assertEqual(config.global_reward_weight, 0.5)

    def test_dual_reward_contract(self):
        reward = DualReward()
        self.assertEqual(reward.local(routing_loop=True), -1.0)
        self.assertEqual(reward.local(ack_received=False), -1.0)
        local = reward.local(
            ack_received=True, available_bandwidth=80.0, maximum_capacity=100.0)
        self.assertAlmostEqual(local, 0.8)

        global_reward = reward.global_reward(
            actual_fct_ms=40.0,
            expected_fct_ms=50.0,
            achieved_throughput=200.0,
            required_throughput=100.0,
            packet_loss_rate=0.1,
        )
        self.assertAlmostEqual(global_reward, 2.9)
        self.assertAlmostEqual(reward.combined(local, terminated=False), 0.4)
        self.assertAlmostEqual(
            reward.combined(local, global_reward, terminated=True), 1.85)

    def test_local_graph_features_and_action_mask(self):
        edges = [
            {"src": 1, "dst": 2, "capacity": 100, "available_bandwidth": 80,
             "delay": 2, "loss": 0.01},
            {"src": 2, "dst": 1, "capacity": 100, "available_bandwidth": 90,
             "delay": 2, "loss": 0.01},
            {"src": 2, "dst": 3, "capacity": 50, "available_bandwidth": 25,
             "delay": 4, "loss": 0.02},
            {"src": 3, "dst": 2, "capacity": 50, "available_bandwidth": 40,
             "delay": 4, "loss": 0.02},
        ]
        observation = build_gart_observation(
            edges,
            current_node=1,
            destination_node=3,
            visited_nodes=[1],
            deadline_ms=50,
        )
        self.assertEqual(observation.node_ids, [1, 2, 3])
        self.assertEqual(observation.action_mask, [False, True, False])
        self.assertAlmostEqual(observation.node_features[0][0], 0.8)
        self.assertAlmostEqual(observation.flow_features[1], 0.25)
        self.assertTrue(all(
            observation.adjacency[index][index]
            for index in range(len(observation.node_ids))))

    def test_two_layer_gat_materializes_only_two_hop_receptive_field(self):
        edges = []
        for src, dst in ((1, 2), (2, 3), (3, 4), (4, 5)):
            for left, right in ((src, dst), (dst, src)):
                edges.append({
                    "src": left,
                    "dst": right,
                    "capacity": 100,
                    "available_bandwidth": 80,
                    "delay": 1,
                    "loss": 0,
                })

        observation = build_gart_observation(
            edges,
            current_node=1,
            destination_node=5,
            visited_nodes=[1],
            deadline_ms=20,
            neighborhood_hops=2,
        )

        self.assertEqual(observation.node_ids, [1, 2, 3])
        self.assertEqual(len(observation.adjacency), 3)
        self.assertEqual(observation.action_mask, [False, True, False])
        self.assertEqual(observation.destination_index, 4)
        self.assertAlmostEqual(observation.flow_features[0], 1.0)

    def test_training_environment_uses_per_hop_dual_reward_contract(self):
        with tempfile.TemporaryDirectory() as directory:
            topology = Path(directory) / "Topology.txt"
            topology.write_text(
                "2 1\n1 2 100 1000 0\n1 1\n",
                encoding="utf-8",
            )
            matrix = Path(directory) / "TM.txt"
            matrix.write_text("0 1 1 0\n", encoding="utf-8")
            environment = TopologyRoutingEnv(
                str(topology), str(matrix), seed=3, link_change_probability=0.0)
            observation = environment.reset()
            valid_indices = [
                index for index, allowed in enumerate(observation.action_mask)
                if allowed
            ]
            self.assertEqual(len(valid_indices), 1)
            next_node = observation.node_ids[valid_indices[0]]
            _next_observation, combined, done, info = environment.step(next_node)
            self.assertTrue(done)
            self.assertTrue(info["delivered"])
            self.assertIsNotNone(info["global_reward"])
            self.assertAlmostEqual(
                combined,
                0.5 * info["local_reward"] + 0.5 * info["global_reward"],
            )


if __name__ == "__main__":
    unittest.main()
