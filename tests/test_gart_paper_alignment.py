import pytest


torch = pytest.importorskip("torch")

from gart.config import GARTConfig
from gart.model import GARTMultiAgentActorCritic
from gart.observation import build_gart_observation
from gart.ppo import GARTPPO
from gart.rollout import GARTRolloutBuffer


def _model_inputs():
    return {
        "node_features": torch.tensor([[[0.8, 0.1, 0.01],
                                         [0.5, 0.4, 0.02],
                                         [0.3, 0.7, 0.05]]]),
        "adjacency": torch.ones(1, 3, 3, dtype=torch.bool),
        "current_node": torch.tensor([0]),
        "flow_features": torch.tensor([[0.75, 0.20, 0.25]]),
        "action_mask": torch.tensor([[False, True, True]]),
    }


def test_flow_features_include_destination_demand_and_deadline():
    observation = build_gart_observation(
        [
            {"src": 1, "dst": 2, "capacity": 100, "delay": 2, "loss": 0.01},
            {"src": 2, "dst": 1, "capacity": 100, "delay": 2, "loss": 0.01},
        ],
        current_node=1,
        destination_node=2,
        traffic_demand=20,
        deadline_ms=50,
    )

    assert observation.flow_features == pytest.approx([1.0, 0.2, 0.25])


def test_each_node_owns_independent_gat_actor_and_critic_parameters():
    model = GARTMultiAgentActorCritic(GARTConfig(), [1, 2])
    first = model.agent(1)
    second = model.agent(2)

    assert first is not second
    assert first.encoder is not second.encoder
    assert first.actor is not second.actor
    assert first.critic is not second.critic
    assert first.encoder.layers[0].projection.weight.data_ptr() != (
        second.encoder.layers[0].projection.weight.data_ptr())


def test_gat_output_responds_to_capacity_delay_and_loss_features():
    config = GARTConfig(gat_dropout=0.0)
    agent = GARTMultiAgentActorCritic(config, [1]).agent(1).eval()
    inputs = _model_inputs()
    baseline = agent.encoder(
        inputs["node_features"], inputs["adjacency"])

    for feature_index in range(3):
        changed = inputs["node_features"].clone()
        changed[0, 1, feature_index] += 0.3
        embedding = agent.encoder(changed, inputs["adjacency"])
        assert not torch.allclose(baseline, embedding)


def test_terminal_global_feedback_reaches_earlier_advantage_via_gae():
    rollout = GARTRolloutBuffer(capacity=2, gamma=1.0, gae_lambda=1.0)
    inputs = _model_inputs()
    rollout.add(
        inputs, torch.tensor([1]), torch.tensor([0.0]),
        torch.tensor([[0.0]]), reward=0.2, done=False, agent_id=1)
    rollout.add(
        inputs, torch.tensor([2]), torch.tensor([0.0]),
        torch.tensor([[0.0]]), reward=1.0, done=True, agent_id=2)

    _, advantages = rollout.compute_returns_and_advantages(
        last_value=0.0, last_done=True)

    assert rollout.rewards == [0.2, 1.0]
    assert advantages.tolist() == pytest.approx([1.2, 1.0])


def test_joint_loss_reaches_gat_actor_and_critic_and_optimizer_owns_all_agents():
    config = GARTConfig(gat_dropout=0.0)
    model = GARTMultiAgentActorCritic(config, [1, 2])
    trainer = GARTPPO(model, config)
    inputs = _model_inputs()
    agent = model.agent(1)
    value, distribution = agent.distribution(
        inputs["node_features"],
        inputs["adjacency"],
        inputs["current_node"],
        inputs["flow_features"],
        inputs["action_mask"],
    )
    loss = -distribution.log_prob(torch.tensor([1])).mean()
    loss = loss + 0.5 * (value.squeeze(-1) - 1.0).pow(2).mean()
    loss.backward()

    assert agent.encoder.layers[0].projection.weight.grad is not None
    assert agent.actor[0].weight.grad is not None
    assert agent.critic[0].weight.grad is not None
    optimized = {
        id(parameter)
        for group in trainer.optimizer.param_groups
        for parameter in group["params"]
    }
    assert optimized == {id(parameter) for parameter in model.parameters()}
