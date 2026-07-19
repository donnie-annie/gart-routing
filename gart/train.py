"""CPU-first PPO training entry point for GART.

Run from the repository root:

    python3 -m gart.train --dataset nsfnet
"""

import argparse
import json
import os
import random

import torch

from .config import GARTConfig
from .model import GARTActorCritic
from .ppo import GARTPPO
from .rewards import DualRewardConfig
from .rollout import GARTRolloutBuffer
from .topology_env import TopologyRoutingEnv
from .topologies import DEFAULT_TOPOLOGY, TOPOLOGIES, get_topology


def parse_args(argv=None):
    parser = argparse.ArgumentParser(description="Train the GART routing policy")
    parser.add_argument(
        "--dataset", choices=tuple(TOPOLOGIES), default=DEFAULT_TOPOLOGY,
        help="topology dataset (default: nsfnet)",
    )
    parser.add_argument("--topology", default=None,
                        help="custom Topology.txt override")
    parser.add_argument("--traffic-matrix", default=None,
                        help="custom traffic-matrix override")
    parser.add_argument("--output", default=None,
                        help="checkpoint path; defaults to models/<dataset>/gart.pt")
    parser.add_argument("--interactions", type=int, default=100000,
                        help="training interaction budget (default: 100000)")
    parser.add_argument("--traffic-intensity", type=float, choices=(0.3, 0.7), default=0.7)
    parser.add_argument("--seed", type=int, default=1)
    parser.add_argument("--cuda", action="store_true", help="use CUDA when available")
    parser.add_argument("--resume", default=None)
    args = parser.parse_args(argv)
    dataset = get_topology(args.dataset)
    args.topology = args.topology or str(dataset.topology_path)
    args.traffic_matrix = args.traffic_matrix or str(dataset.traffic_matrix_path)
    args.output = args.output or str(dataset.default_model_path)
    return args


def train(args):
    random.seed(args.seed)
    torch.manual_seed(args.seed)
    device = torch.device("cuda" if args.cuda and torch.cuda.is_available() else "cpu")
    config = GARTConfig()
    reward_config = DualRewardConfig.from_gart_config(config)
    environment = TopologyRoutingEnv(
        topology_path=args.topology,
        traffic_matrix_path=args.traffic_matrix,
        traffic_intensity=args.traffic_intensity,
        seed=args.seed,
        reward_config=reward_config,
        neighborhood_hops=config.gat_layers,
    )
    model = GARTActorCritic(config).to(device)
    trainer = GARTPPO(model, config)

    if args.resume:
        checkpoint = torch.load(args.resume, map_location=device)
        model.load_state_dict(checkpoint["model_state_dict"])
        if checkpoint.get("optimizer_state_dict"):
            trainer.optimizer.load_state_dict(checkpoint["optimizer_state_dict"])

    rollout = GARTRolloutBuffer(
        config.rollout_length,
        gamma=config.discount_factor,
        gae_lambda=config.gae_lambda,
    )
    observation = environment.reset()
    last_done = False

    for interaction in range(1, args.interactions + 1):
        tensors = observation.to_tensors(device)
        with torch.no_grad():
            value, action, log_probability, _ = model.act(
                tensors["node_features"],
                tensors["adjacency"],
                tensors["current_node"],
                tensors["flow_features"],
                tensors["action_mask"],
            )
        next_node = observation.node_ids[int(action.item())]
        next_observation, reward, done, info = environment.step(next_node)
        rollout.add(tensors, action, log_probability, value, reward, done)
        last_done = done
        observation = environment.reset() if done else next_observation

        if rollout.full or interaction == args.interactions:
            if last_done:
                last_value = 0.0
            else:
                next_tensors = observation.to_tensors(device)
                with torch.no_grad():
                    last_value = model.forward(
                        next_tensors["node_features"],
                        next_tensors["adjacency"],
                        next_tensors["current_node"],
                        next_tensors["flow_features"],
                    )[0].item()
            rollout.compute_returns_and_advantages(last_value, last_done)
            metrics = trainer.update(rollout, device)
            metrics.update({
                "interaction": interaction,
                "flow_type": info["flow_type"],
                "delivered": info["delivered"],
            })
            print(json.dumps(metrics, sort_keys=True))
            rollout.clear()

    output_dir = os.path.dirname(os.path.abspath(args.output))
    os.makedirs(output_dir, exist_ok=True)
    torch.save(model.checkpoint(
        optimizer=trainer.optimizer,
        extra={
            "dataset": args.dataset,
            "seed": args.seed,
            "interactions": args.interactions,
            "traffic_intensity": args.traffic_intensity,
            "observation_scope": "bounded_local",
            "neighborhood_hops": config.gat_layers,
        },
    ), args.output)
    return args.output


def main(argv=None):
    args = parse_args(argv)
    output = train(args)
    print("saved GART checkpoint to %s" % output)


if __name__ == "__main__":
    main()
