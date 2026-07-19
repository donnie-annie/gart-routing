import importlib
import sys
from pathlib import Path


ROOT = Path(__file__).resolve().parents[1]
if str(ROOT) not in sys.path:
    sys.path.insert(0, str(ROOT))


def test_default_drl_route_mode_is_shadow_or_hybrid_safe(monkeypatch):
    monkeypatch.delenv("DRL_ROUTE_MODE", raising=False)
    import common_config
    importlib.reload(common_config)

    assert common_config.DRL_ROUTE_MODE in {"shadow", "hybrid"}


def test_drl_route_mode_accepts_environment_override(monkeypatch):
    monkeypatch.setenv("DRL_ROUTE_MODE", "spf")
    import common_config
    importlib.reload(common_config)

    assert common_config.DRL_ROUTE_MODE == "spf"


def test_drl_thresholds_are_available(monkeypatch):
    monkeypatch.setenv("DRL_INFERENCE_TIMEOUT_MS", "80")
    monkeypatch.setenv("DRL_MIN_CONFIDENCE", "0.65")
    import common_config
    importlib.reload(common_config)

    assert common_config.DRL_INFERENCE_TIMEOUT_MS == 80
    assert common_config.DRL_MIN_CONFIDENCE == 0.65
