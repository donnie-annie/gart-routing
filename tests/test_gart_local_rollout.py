import pytest


torch = pytest.importorskip("torch")

from gart.rollout import GARTRolloutBuffer


def _transition(node_count, current_index=0):
    adjacency = torch.eye(node_count, dtype=torch.bool).unsqueeze(0)
    if node_count > 1:
        adjacency[0, current_index, 1] = True
    action_mask = torch.zeros(1, node_count, dtype=torch.bool)
    action_mask[0, 1 if node_count > 1 else 0] = True
    return {
        "node_features": torch.zeros(1, node_count, 3),
        "adjacency": adjacency,
        "current_node": torch.tensor([current_index]),
        "flow_features": torch.zeros(1, 2),
        "action_mask": action_mask,
    }


def test_rollout_pads_variable_local_neighborhoods_only_to_batch_maximum():
    rollout = GARTRolloutBuffer(capacity=2)
    rollout.add(
        _transition(2), torch.tensor([1]), torch.tensor([0.0]),
        torch.tensor([[0.0]]), reward=0.0, done=False)
    rollout.add(
        _transition(4), torch.tensor([1]), torch.tensor([0.0]),
        torch.tensor([[0.0]]), reward=1.0, done=True)
    rollout.compute_returns_and_advantages(last_value=0.0, last_done=True)

    tensors = rollout.tensors("cpu")

    assert tensors["node_features"].shape == (2, 4, 3)
    assert tensors["adjacency"].shape == (2, 4, 4)
    assert tensors["action_mask"].shape == (2, 4)
    assert not tensors["action_mask"][0, 2:].any()
    assert tensors["adjacency"][0, 2, 2]
    assert tensors["adjacency"][0, 3, 3]
