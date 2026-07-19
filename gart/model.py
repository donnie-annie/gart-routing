"""Flow-conditioned multi-head GAT Actor-Critic used by GART."""

import torch
import torch.nn as nn
import torch.nn.functional as F

from .config import GARTConfig


class MultiHeadGATLayer(nn.Module):
    """Vanilla multi-head graph attention implementing Equations (5)-(7)."""

    def __init__(self, input_dim, heads, head_dim, dropout=0.1, negative_slope=0.2):
        super().__init__()
        self.heads = int(heads)
        self.head_dim = int(head_dim)
        self.projection = nn.Linear(input_dim, self.heads * self.head_dim, bias=False)
        self.attention_source = nn.Parameter(torch.empty(self.heads, self.head_dim))
        self.attention_target = nn.Parameter(torch.empty(self.heads, self.head_dim))
        self.dropout = nn.Dropout(dropout)
        self.negative_slope = negative_slope
        self.reset_parameters()

    def reset_parameters(self):
        nn.init.xavier_uniform_(self.projection.weight, gain=1.414)
        nn.init.xavier_uniform_(self.attention_source, gain=1.414)
        nn.init.xavier_uniform_(self.attention_target, gain=1.414)

    def forward(self, node_features, adjacency):
        """
        Args:
            node_features: ``[batch, nodes, input_dim]``.
            adjacency: boolean ``[batch, nodes, nodes]`` including self loops.
        """
        batch_size, node_count, _ = node_features.shape
        projected = self.projection(node_features).view(
            batch_size, node_count, self.heads, self.head_dim)

        source_score = torch.einsum("bnhd,hd->bhn", projected, self.attention_source)
        target_score = torch.einsum("bnhd,hd->bhn", projected, self.attention_target)
        scores = source_score.unsqueeze(-1) + target_score.unsqueeze(-2)
        scores = F.leaky_relu(scores, negative_slope=self.negative_slope)

        mask = adjacency.to(dtype=torch.bool).unsqueeze(1)
        scores = scores.masked_fill(~mask, torch.finfo(scores.dtype).min)
        coefficients = F.softmax(scores, dim=-1)
        coefficients = self.dropout(coefficients)

        aggregated = torch.einsum("bhij,bjhd->bihd", coefficients, projected)
        return aggregated.reshape(batch_size, node_count, self.heads * self.head_dim)


class GARTEncoder(nn.Module):
    """Two-layer, four-head localized GAT from Table III by default."""

    def __init__(self, config):
        super().__init__()
        layers = []
        input_dim = config.node_feature_dim
        for _ in range(config.gat_layers):
            layers.append(MultiHeadGATLayer(
                input_dim=input_dim,
                heads=config.attention_heads,
                head_dim=config.embedding_dim_per_head,
                dropout=config.gat_dropout,
                negative_slope=config.leaky_relu_slope,
            ))
            input_dim = config.embedding_dim
        self.layers = nn.ModuleList(layers)
        self.dropout = nn.Dropout(config.gat_dropout)

    def forward(self, node_features, adjacency):
        embedding = node_features
        for layer_index, layer in enumerate(self.layers):
            embedding = F.relu(layer(embedding, adjacency))
            # Algorithm 1 normalizes the embedding after every GAT layer.
            embedding = F.normalize(embedding, p=2, dim=-1, eps=1e-12)
            if layer_index + 1 < len(self.layers):
                embedding = self.dropout(embedding)
        return embedding


def _mlp(input_dim, hidden_dims, output_dim):
    layers = []
    current = input_dim
    for width in hidden_dims:
        layers.extend((nn.Linear(current, width), nn.ReLU()))
        current = width
    layers.append(nn.Linear(current, output_dim))
    return nn.Sequential(*layers)


class GARTActorCritic(nn.Module):
    """Decentralized next-hop Actor with a training-only state-value Critic."""

    algorithm = "GART"

    def __init__(self, config=None):
        super().__init__()
        self.config = config or GARTConfig()
        self.encoder = GARTEncoder(self.config)

        actor_input = self.config.embedding_dim * 2 + self.config.flow_feature_dim
        critic_input = self.config.embedding_dim + self.config.flow_feature_dim
        self.actor = _mlp(actor_input, self.config.actor_hidden, 1)
        self.critic = _mlp(critic_input, self.config.critic_hidden, 1)

    @staticmethod
    def _current_embedding(embeddings, current_node):
        batch = torch.arange(embeddings.size(0), device=embeddings.device)
        return embeddings[batch, current_node]

    def forward(self, node_features, adjacency, current_node, flow_features):
        embeddings = self.encoder(node_features, adjacency)
        current = self._current_embedding(embeddings, current_node)

        node_count = embeddings.size(1)
        actor_input = torch.cat((
            current.unsqueeze(1).expand(-1, node_count, -1),
            embeddings,
            flow_features.unsqueeze(1).expand(-1, node_count, -1),
        ), dim=-1)
        logits = self.actor(actor_input).squeeze(-1)

        critic_input = torch.cat((current, flow_features), dim=-1)
        value = self.critic(critic_input)
        return value, logits

    def distribution(self, node_features, adjacency, current_node,
                     flow_features, action_mask):
        value, logits = self.forward(
            node_features, adjacency, current_node, flow_features)
        action_mask = action_mask.to(dtype=torch.bool)
        if not bool(action_mask.any(dim=-1).all()):
            raise ValueError("GART action mask contains a state with no valid next hop")
        masked_logits = logits.masked_fill(~action_mask, torch.finfo(logits.dtype).min)
        return value, torch.distributions.Categorical(logits=masked_logits)

    def act(self, node_features, adjacency, current_node, flow_features,
            action_mask, deterministic=False):
        value, distribution = self.distribution(
            node_features, adjacency, current_node, flow_features, action_mask)
        if deterministic:
            action = distribution.probs.argmax(dim=-1)
        else:
            action = distribution.sample()
        log_probability = distribution.log_prob(action)
        return value, action, log_probability, distribution.probs

    def evaluate_actions(self, node_features, adjacency, current_node,
                         flow_features, action_mask, actions):
        value, distribution = self.distribution(
            node_features, adjacency, current_node, flow_features, action_mask)
        return value, distribution.log_prob(actions), distribution.entropy()

    def checkpoint(self, optimizer=None, extra=None):
        payload = {
            "algorithm": self.algorithm,
            "config": self.config.to_dict(),
            "model_state_dict": self.state_dict(),
        }
        if optimizer is not None:
            payload["optimizer_state_dict"] = optimizer.state_dict()
        if extra:
            payload["extra"] = dict(extra)
        return payload

    @classmethod
    def from_checkpoint(cls, checkpoint, map_location="cpu"):
        if isinstance(checkpoint, str):
            checkpoint = torch.load(checkpoint, map_location=map_location)
        config = GARTConfig.from_dict(checkpoint.get("config", {}))
        model = cls(config)
        model.load_state_dict(checkpoint["model_state_dict"])
        return model
