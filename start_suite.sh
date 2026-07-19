#!/usr/bin/env bash
set -euo pipefail

cd "$(dirname "$0")"
mkdir -p logs
EXTERNAL_INTF="${1:-}"
PYTHON_BIN="${PYTHON_BIN:-python3}"
SERVER_AGENT_ROUTE_MODE="${SERVER_AGENT_ROUTE_MODE:-hybrid}"
ROUTING_ALGORITHM="${ROUTING_ALGORITHM:-gart}"
GART_TOPOLOGY="${GART_TOPOLOGY:-nsfnet}"
PATH_SERVICE_MODEL="${PATH_SERVICE_MODEL:-models/${GART_TOPOLOGY}/gart.pt}"
TOPOLOGY_FILE="${TOPOLOGY_FILE:-topology/${GART_TOPOLOGY}/Topology.txt}"
CONTROLLER_PORTS="${CONTROLLER_PORTS:-6654}"

if [ -n "${PATH_SERVICE_PYTHON:-}" ]; then
  :
elif [ -x "$HOME/miniconda3/envs/ryu_drl_s/bin/python" ]; then
  PATH_SERVICE_PYTHON="$HOME/miniconda3/envs/ryu_drl_s/bin/python"
else
  PATH_SERVICE_PYTHON="$PYTHON_BIN"
fi

cleanup() {
  ./stop_suite.sh >/dev/null 2>&1 || true
}
trap cleanup EXIT INT TERM

if [ -f logs/path_service.pid ] || [ -f logs/server_agent.pid ] || [ -f logs/start_controllers.pid ]; then
  echo "Existing pid files found under logs/. Run ./stop_suite.sh first if the suite is already running."
fi

"$PATH_SERVICE_PYTHON" -m gart.path_service --topo "$GART_TOPOLOGY" --port 8889 \
  --algorithm "$ROUTING_ALGORITHM" --model "$PATH_SERVICE_MODEL" > logs/path_service.log 2>&1 &
echo $! > logs/path_service.pid

sleep 1

"$PYTHON_BIN" server_agent.py "$SERVER_AGENT_ROUTE_MODE" > logs/server_agent.stdout.log 2>&1 &
echo $! > logs/server_agent.pid

sleep 1

if [ -n "$EXTERNAL_INTF" ]; then
  export EXTERNAL_LINK_PORTS="${EXTERNAL_LINK_PORTS:-1:20}"
  echo "Hybrid physical attachment enabled: $EXTERNAL_INTF -> s1:port20"
  echo "Controller external link whitelist: $EXTERNAL_LINK_PORTS"
fi

"$PYTHON_BIN" -u start_controllers.py start --ports "$CONTROLLER_PORTS" > logs/controllers.log 2>&1 &
echo $! > logs/start_controllers.pid

echo "GART Routing Suite started"
echo "server socket: 6001"
echo "Web UI: http://localhost:6009"
echo "GART path_service: 127.0.0.1:8889"
echo "routing algorithm: $ROUTING_ALGORITHM"
echo "server_agent route mode: $SERVER_AGENT_ROUTE_MODE"
echo "controller ports: $CONTROLLER_PORTS"
echo "topology: $GART_TOPOLOGY ($TOPOLOGY_FILE)"
echo "Starting the Mininet topology in this terminal..."
echo "Exit the Mininet CLI to stop the suite."

if [ -n "$EXTERNAL_INTF" ]; then
  sudo "$PYTHON_BIN" testbed/topology_launcher.py --topology "$TOPOLOGY_FILE" \
    --external-intf "$EXTERNAL_INTF" 2>&1 | tee logs/mininet_topology.log
else
  sudo "$PYTHON_BIN" testbed/topology_launcher.py --topology "$TOPOLOGY_FILE" \
    2>&1 | tee logs/mininet_topology.log
fi
