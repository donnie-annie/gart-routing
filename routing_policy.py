"""Policy-aware edge weights for fallback path computation."""

def compute_edge_weight(route_policy, edge_data):
    """Return the edge cost for the selected routing policy."""
    delay = edge_data.get('delay', 1)
    bw = edge_data.get('bw', 1)
    loss = edge_data.get('loss', 0)
    edge_type = edge_data.get('edge_type')

    if edge_type != 'switch_link':
        return float(edge_data.get('weight', 1))

    if route_policy == 'min_delay':
        return max(float(delay), 0.0001)
    if route_policy == 'max_bandwidth':
        return 1.0 / max(float(bw), 0.0001)
    if route_policy == 'min_loss':
        return max(float(loss), 0.0) + 0.0001
    if route_policy == 'hybrid':
        return max(float(delay), 0.0) * (1.0 + max(float(loss), 0.0)) / max(float(bw), 0.0001)

    return float(edge_data.get('weight', 1))
