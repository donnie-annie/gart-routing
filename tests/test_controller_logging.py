import sys
from pathlib import Path


ROOT = Path(__file__).resolve().parents[1]
if str(ROOT) not in sys.path:
    sys.path.insert(0, str(ROOT))


def test_controller_manager_uses_project_logs_for_background_controller_output():
    from start_controllers import ControllerManager

    manager = ControllerManager()

    assert manager.log_dir == ROOT / "logs"
    assert manager.controller_log_path(6654) == ROOT / "logs" / "ryu_controller_6654.log"


def test_controller_status_no_longer_points_to_tmp_logs():
    text = (ROOT / "start_controllers.py").read_text(encoding="utf-8")

    assert "/tmp/ryu_controller_" not in text
    assert "controller_log_path" in text
