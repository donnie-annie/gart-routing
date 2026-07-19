import sys
from pathlib import Path


ROOT = Path(__file__).resolve().parents[1]
if str(ROOT) not in sys.path:
    sys.path.insert(0, str(ROOT))


def test_parse_route_mode_arg_accepts_all_modes():
    import server_agent

    for mode in ("spf", "shadow", "hybrid", "drl"):
        assert server_agent.parse_route_mode_arg([mode]) == mode


def test_parse_route_mode_arg_defaults_to_configured_mode():
    import server_agent

    assert server_agent.parse_route_mode_arg([]) == server_agent.DRL_ROUTE_MODE
