import sys
from pathlib import Path


ROOT = Path(__file__).resolve().parents[1]
if str(ROOT) not in sys.path:
    sys.path.insert(0, str(ROOT))

from web_api import _prepare_node_data_for_graph


def test_graph_node_payload_omits_flow_table_by_default():
    node_data = {
        "node_type": "switch",
        "flow_table": [{"id": i, "match": "x" * 100} for i in range(50)],
        "gateway_ip": "10.0.0.1",
    }

    result = _prepare_node_data_for_graph(node_data, include_flows=False)

    assert "flow_table" not in result
    assert result["flow_count"] == 50
    assert result["gateway_ip"] == "10.0.0.1"


def test_graph_node_payload_can_include_flow_table_on_demand():
    flow_table = [{"id": 1, "match": "ip"}]
    node_data = {
        "node_type": "switch",
        "flow_table": flow_table,
    }

    result = _prepare_node_data_for_graph(node_data, include_flows=True)

    assert result["flow_table"] == flow_table
    assert result["flow_count"] == 1
