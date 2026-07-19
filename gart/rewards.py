"""Local and global rewards used by GART."""

from dataclasses import dataclass
import math


def _finite(value, default=0.0):
    try:
        value = float(value)
    except (TypeError, ValueError):
        return float(default)
    return value if math.isfinite(value) else float(default)


def _clamp(value, lower, upper):
    return max(lower, min(upper, value))


@dataclass(frozen=True)
class DualRewardConfig:
    loop_penalty: float = -1.0
    no_ack_penalty: float = -1.0
    residual_bandwidth_weight: float = 1.0
    deadline_reward_weight: float = 1.0
    throughput_reward_weight: float = 1.0
    loss_penalty_weight: float = 1.0
    global_reward_bias: float = 0.0
    local_weight: float = 0.5
    global_weight: float = 0.5

    @classmethod
    def from_gart_config(cls, config):
        return cls(
            loop_penalty=config.loop_penalty,
            no_ack_penalty=config.no_ack_penalty,
            residual_bandwidth_weight=config.residual_bandwidth_weight,
            deadline_reward_weight=config.deadline_reward_weight,
            throughput_reward_weight=config.throughput_reward_weight,
            loss_penalty_weight=config.loss_penalty_weight,
            global_reward_bias=config.global_reward_bias,
            local_weight=config.local_reward_weight,
            global_weight=config.global_reward_weight,
        )


class DualReward:
    """Compute GART feedback without coupling it to a specific simulator."""

    def __init__(self, config=None):
        self.config = config or DualRewardConfig()

    def local(self, routing_loop=False, ack_received=True,
              available_bandwidth=0.0, maximum_capacity=1.0):
        """Equation (2): loop/no-ACK penalty or normalized bandwidth reward."""
        if routing_loop:
            return float(self.config.loop_penalty)
        if not ack_received:
            return float(self.config.no_ack_penalty)

        available = max(_finite(available_bandwidth), 0.0)
        capacity = max(_finite(maximum_capacity, 1.0), 1e-12)
        residual_ratio = _clamp(available / capacity, 0.0, 1.0)
        return self.config.residual_bandwidth_weight * residual_ratio

    def global_reward(self, actual_fct_ms, expected_fct_ms,
                      achieved_throughput, required_throughput,
                      packet_loss_rate):
        """Equation (3): deadline indicator + throughput ratio - packet loss."""
        actual = max(_finite(actual_fct_ms), 0.0)
        expected = max(_finite(expected_fct_ms), 0.0)
        on_time = 1.0 if actual <= expected else 0.0

        required = max(_finite(required_throughput, 1.0), 1e-12)
        throughput_ratio = max(_finite(achieved_throughput), 0.0) / required
        loss_rate = _clamp(_finite(packet_loss_rate), 0.0, 1.0)

        return (
            self.config.deadline_reward_weight * on_time
            + self.config.throughput_reward_weight * throughput_ratio
            - self.config.loss_penalty_weight * loss_rate
            + self.config.global_reward_bias
        )

    def combined(self, local_reward, global_reward=None, terminated=False):
        """Equation (4), applying global feedback only on terminal transitions."""
        reward = self.config.local_weight * _finite(local_reward)
        if terminated and global_reward is not None:
            reward += self.config.global_weight * _finite(global_reward)
        return reward
