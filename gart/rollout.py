"""On-policy trajectory storage with terminal global rewards and GAE."""

import torch


class GARTRolloutBuffer:
    """Store Algorithm 2 transitions for one fixed topology rollout."""

    def __init__(self, capacity, gamma=0.99, gae_lambda=0.95):
        self.capacity = int(capacity)
        self.gamma = float(gamma)
        self.gae_lambda = float(gae_lambda)
        self.clear()

    def clear(self):
        self.node_features = []
        self.adjacencies = []
        self.current_nodes = []
        self.flow_features = []
        self.action_masks = []
        self.actions = []
        self.log_probabilities = []
        self.values = []
        self.rewards = []
        self.dones = []
        self.returns = None
        self.advantages = None

    def __len__(self):
        return len(self.rewards)

    @property
    def full(self):
        return len(self) >= self.capacity

    @staticmethod
    def _cpu(value):
        return value.detach().cpu()

    def add(self, observation_tensors, action, log_probability, value,
            reward, done):
        if self.full:
            raise RuntimeError("GART rollout is already full")
        self.node_features.append(self._cpu(observation_tensors["node_features"].squeeze(0)))
        self.adjacencies.append(self._cpu(observation_tensors["adjacency"].squeeze(0)))
        self.current_nodes.append(self._cpu(observation_tensors["current_node"].squeeze(0)))
        self.flow_features.append(self._cpu(observation_tensors["flow_features"].squeeze(0)))
        self.action_masks.append(self._cpu(observation_tensors["action_mask"].squeeze(0)))
        self.actions.append(self._cpu(action.reshape(())))
        self.log_probabilities.append(self._cpu(log_probability.reshape(())))
        self.values.append(self._cpu(value.reshape(())))
        self.rewards.append(float(reward))
        self.dones.append(bool(done))

    def compute_returns_and_advantages(self, last_value=0.0, last_done=False):
        if not self.rewards:
            raise RuntimeError("cannot compute GAE for an empty rollout")

        values = torch.stack(self.values).float()
        rewards = torch.tensor(self.rewards, dtype=torch.float32)
        dones = torch.tensor(self.dones, dtype=torch.float32)
        advantages = torch.zeros_like(rewards)
        gae = torch.tensor(0.0)
        next_value = torch.as_tensor(last_value, dtype=torch.float32).reshape(())

        for step in reversed(range(len(self))):
            next_non_terminal = 1.0 - (dones[step] if step + 1 < len(self) else float(last_done))
            if step + 1 < len(self):
                next_value = values[step + 1]
                next_non_terminal = 1.0 - dones[step]
            delta = rewards[step] + self.gamma * next_value * next_non_terminal - values[step]
            gae = delta + self.gamma * self.gae_lambda * next_non_terminal * gae
            advantages[step] = gae

        self.advantages = advantages
        self.returns = advantages + values
        return self.returns, self.advantages

    def tensors(self, device):
        if self.returns is None or self.advantages is None:
            raise RuntimeError("compute_returns_and_advantages must be called first")

        # Each agent decision uses a bounded local subgraph, whose node count
        # varies with the current node degree.  Pad only to the largest local
        # neighborhood in this rollout so PPO can still form dense batches
        # without restoring a topology-wide N x N tensor.
        max_nodes = max(item.size(0) for item in self.node_features)

        def pad_features(item):
            padded = torch.zeros(
                max_nodes, item.size(1), dtype=item.dtype)
            padded[:item.size(0)] = item
            return padded

        def pad_adjacency(item):
            padded = torch.zeros(
                max_nodes, max_nodes, dtype=item.dtype)
            size = item.size(0)
            padded[:size, :size] = item
            # Isolate padded nodes so their rows have a valid softmax domain.
            for index in range(size, max_nodes):
                padded[index, index] = True
            return padded

        def pad_action_mask(item):
            padded = torch.zeros(max_nodes, dtype=item.dtype)
            padded[:item.size(0)] = item
            return padded

        return {
            "node_features": torch.stack([
                pad_features(item) for item in self.node_features
            ]).to(device),
            "adjacency": torch.stack([
                pad_adjacency(item) for item in self.adjacencies
            ]).to(device),
            "current_node": torch.stack(self.current_nodes).long().to(device),
            "flow_features": torch.stack(self.flow_features).to(device),
            "action_mask": torch.stack([
                pad_action_mask(item) for item in self.action_masks
            ]).bool().to(device),
            "actions": torch.stack(self.actions).long().to(device),
            "old_log_probabilities": torch.stack(self.log_probabilities).to(device),
            "old_values": torch.stack(self.values).to(device),
            "returns": self.returns.to(device),
            "advantages": self.advantages.to(device),
        }
