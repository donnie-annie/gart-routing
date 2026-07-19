import sys
from pathlib import Path


ROOT = Path(__file__).resolve().parents[1]
if str(ROOT) not in sys.path:
    sys.path.insert(0, str(ROOT))

from server_agent import ServerAgent


def test_shadow_mode_installs_fallback_but_records_drl_advice():
    agent = ServerAgent.__new__(ServerAgent)
    fallback = {"status": "ok", "path": ["h1", 1, 2, "h2"], "path_source": "dijkstra"}
    drl = {"status": "ok", "path": ["h1", 1, 3, 2, "h2"], "decision_source": "drl_model", "model_used": True}

    result = agent._choose_final_path_response({}, drl, fallback, "shadow")

    assert result["path"] == ["h1", 1, 2, "h2"]
    assert result["path_source"] == "shadow_fallback"
    assert result["drl_shadow"]["path"] == ["h1", 1, 3, 2, "h2"]
    assert result["drl_shadow"]["model_used"] is True
