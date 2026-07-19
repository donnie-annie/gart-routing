import importlib.util
from pathlib import Path


ROOT = Path(__file__).resolve().parents[1]
PATH_SERVICE = ROOT / "gart" / "path_service.py"


def load_path_service_module():
    spec = importlib.util.spec_from_file_location("path_service_under_test", PATH_SERVICE)
    module = importlib.util.module_from_spec(spec)
    spec.loader.exec_module(module)
    return module


def test_decision_metadata_helper_marks_model_path():
    module = load_path_service_module()

    result = module._decision("drl_model", [1, 2, 3], model_used=True, fallback_reason=None)

    assert result["path"] == [1, 2, 3]
    assert result["decision_source"] == "drl_model"
    assert result["model_used"] is True
    assert result["fallback_reason"] is None


def test_decision_metadata_helper_marks_fallback():
    module = load_path_service_module()

    result = module._decision("dijkstra", [1, 4], model_used=False, fallback_reason="out_of_drl_range")

    assert result["decision_source"] == "dijkstra"
    assert result["model_used"] is False
    assert result["fallback_reason"] == "out_of_drl_range"
