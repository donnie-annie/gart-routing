# GART package

This package contains the trainable GART policy and its online next-hop service.

## Component map

| Component | Implementation |
|---|---|
| Local observation: capacity, delay, loss | `observation.py` |
| Available-neighbor action mask | `observation.py` and `model.py` |
| Local reward | `rewards.py::DualReward.local` |
| Deadline/throughput/loss global reward | `rewards.py::DualReward.global_reward` |
| Terminal dual reward | `rewards.py::DualReward.combined` |
| Multi-head GAT | `model.py::MultiHeadGATLayer` |
| Flow-conditioned Actor-Critic | `model.py::GARTActorCritic` |
| GAE and rollout | `rollout.py` |
| PPO loss | `ppo.py` |
| Multi-flow training loop | `train.py` |
| Dynamic topology training backend | `topology_env.py` |
| Decentralized online next-hop execution | `path_service.py` |

The model uses two GAT layers and materializes only the current agent's induced
two-hop subgraph.  A reusable topology index keeps state construction local,
and variable neighborhood sizes are padded only to the largest local graph in
each PPO rollout.  Each GAT layer has four attention heads with a 16-dimensional
output per head. Actor and Critic MLPs both use hidden widths 64/64. Embeddings
are L2-normalized after every GAT layer, and invalid or already-visited next
hops are masked before sampling.

The global reward is attached only to the terminal transition. GAE propagates
its effect to earlier per-hop decisions.

## Defaults

- `topologies.py` is the canonical dataset catalog; `nsfnet` is the default.
- Flow profiles are EU 5%/20 ms, MU 15%/50 ms, LU 70%/100 ms, and RT
  10%/200 ms.
- `GARTConfig` exposes all model, optimizer, rollout, and reward parameters.
- CPU is the default training device; CUDA can be enabled with `--cuda`.
- `TopologyRoutingEnv` provides offline training. Online execution uses the
  path service and the existing controller suite.
