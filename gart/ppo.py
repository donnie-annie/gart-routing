"""Clipped PPO update corresponding to Equations (12)-(15)."""

import torch
import torch.nn as nn


class GARTPPO:
    def __init__(self, model, config):
        self.model = model
        self.config = config
        self.optimizer = torch.optim.Adam(
            model.parameters(), lr=config.learning_rate)

    def update(self, rollout, device):
        data = rollout.tensors(device)
        advantages = data["advantages"]
        advantages = (advantages - advantages.mean()) / (advantages.std() + 1e-8)
        sample_count = advantages.numel()

        metrics = {"policy_loss": 0.0, "value_loss": 0.0, "entropy": 0.0}
        updates = 0
        for _ in range(self.config.ppo_epochs):
            order = torch.randperm(sample_count, device=device)
            for start in range(0, sample_count, self.config.mini_batch_size):
                indices = order[start:start + self.config.mini_batch_size]
                value, log_probability, entropy = self.model.evaluate_actions(
                    data["node_features"][indices],
                    data["adjacency"][indices],
                    data["current_node"][indices],
                    data["flow_features"][indices],
                    data["action_mask"][indices],
                    data["actions"][indices],
                )
                value = value.squeeze(-1)
                ratio = torch.exp(log_probability - data["old_log_probabilities"][indices])
                objective = ratio * advantages[indices]
                clipped = torch.clamp(
                    ratio,
                    1.0 - self.config.ppo_clip,
                    1.0 + self.config.ppo_clip,
                ) * advantages[indices]
                policy_loss = -torch.min(objective, clipped).mean()
                value_loss = 0.5 * (value - data["returns"][indices]).pow(2).mean()
                entropy_mean = entropy.mean()
                loss = (
                    policy_loss
                    + self.config.value_loss_coefficient * value_loss
                    - self.config.entropy_coefficient * entropy_mean
                )

                self.optimizer.zero_grad()
                loss.backward()
                nn.utils.clip_grad_norm_(
                    self.model.parameters(), self.config.max_gradient_norm)
                self.optimizer.step()

                metrics["policy_loss"] += float(policy_loss.detach().cpu())
                metrics["value_loss"] += float(value_loss.detach().cpu())
                metrics["entropy"] += float(entropy_mean.detach().cpu())
                updates += 1

        for key in metrics:
            metrics[key] /= max(updates, 1)
        return metrics
