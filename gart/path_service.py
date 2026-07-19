"""GART routing service with topology-aware Dijkstra fallback.

Run the primary implementation from the repository root with::

    python3 -m gart.path_service --topo nsfnet --port 8889

Missing models always fall back to topology-aware Dijkstra.
"""

import argparse
import json
import os
import random
import socket
import sys
import time
import threading

import numpy as np
try:
    import torch
except ImportError as exc:
    torch = None
    TORCH_IMPORT_ERROR = exc
else:
    TORCH_IMPORT_ERROR = None

SERVICE_DIR = os.path.dirname(os.path.abspath(__file__))
PROJECT_ROOT = os.path.dirname(SERVICE_DIR)
TOPOLOGY_ROOT = os.path.join(PROJECT_ROOT, "topology")
DEFAULT_GART_MODEL = os.path.join(
    PROJECT_ROOT, "models", "nsfnet", "gart.pt")

# Import the primary package when this file is launched directly.
sys.path.insert(0, PROJECT_ROOT)


def _resolve_service_path(path, topo_name="nsfnet"):
    if not path:
        return os.path.join(
            PROJECT_ROOT, "models", str(topo_name).lower(), "gart.pt")
    if os.path.isabs(path):
        return path
    return os.path.join(PROJECT_ROOT, path)

GARTActorCritic = None
GARTConfig = None
GARTTopologyIndex = None
build_gart_observation = None
load_topology_edges = None

if torch is not None:
    try:
        from gart.config import GARTConfig                 # noqa: E402
        from gart.model import GARTActorCritic             # noqa: E402
        from gart.observation import (                     # noqa: E402
            GARTTopologyIndex,
            build_gart_observation,
            load_topology_edges,
        )
    except Exception as exc:
        GART_IMPORT_ERROR = exc
    else:
        GART_IMPORT_ERROR = None
else:
    GART_IMPORT_ERROR = TORCH_IMPORT_ERROR


try:
    import networkx as nx
    HAS_NX = True
except ImportError:
    HAS_NX = False
    print("[警告] networkx 未安装，Dijkstra 回退将使用简易 BFS")


def _normalize_topo_edge(edge):
    if isinstance(edge, dict):
        src = edge.get("src")
        dst = edge.get("dst")
        weight = edge.get("weight", 1)
    else:
        src = edge[0]
        dst = edge[1]
        weight = edge[2] if len(edge) > 2 else 1
    try:
        weight = float(weight)
        if not np.isfinite(weight) or weight < 0:
            weight = 1.0
    except Exception:
        weight = 1.0
    return int(src), int(dst), weight


def _dijkstra_on_edges(topo_edges, src, dst):
    """Compute a shortest path over controller-provided directed edges."""
    if not topo_edges:
        return None

    if HAS_NX:
        G = nx.DiGraph()
        for edge in topo_edges:
            u, v, weight = _normalize_topo_edge(edge)
            G.add_edge(u, v, weight=weight)
        if src not in G or dst not in G:
            return None
        try:
            path = nx.shortest_path(G, src, dst, weight="weight")
            return path
        except nx.NetworkXNoPath:
            return None
        except Exception:
            return None
    else:
        from collections import deque, defaultdict
        adj = defaultdict(list)
        for edge in topo_edges:
            u, v, _ = _normalize_topo_edge(edge)
            adj[u].append(v)
        visited = set()
        queue = deque()
        queue.append((src, [src]))
        visited.add(src)
        while queue:
            node, path = queue.popleft()
            if node == dst:
                return path
            for neighbor in adj[node]:
                if neighbor not in visited:
                    visited.add(neighbor)
                    queue.append((neighbor, path + [neighbor]))
        return None


def _decision(decision_source, path, model_used=False, fallback_reason=None, confidence=None):
    return {
        "path": path,
        "decision_source": decision_source,
        "model_used": bool(model_used),
        "fallback_reason": fallback_reason,
        "confidence": confidence,
    }


class GARTPathService(object):
    """Serve GART routing decisions over a local TCP socket."""

    def __init__(self, topo_name="nsfnet", port=8889, model_path=None,
                 algorithm="gart"):
        self.port = port
        self.topo_name = topo_name
        self.algorithm_requested = (algorithm or "auto").strip().lower()
        if self.algorithm_requested not in {"auto", "gart"}:
            raise ValueError("algorithm must be one of: auto, gart")
        self.model_path = _resolve_service_path(model_path, topo_name)

        print("[初始化] 拓扑: %s, 端口: %d, 算法: %s"
              % (topo_name, port, self.algorithm_requested))

        if torch is None:
            raise RuntimeError("PyTorch runtime unavailable: %s" % TORCH_IMPORT_ERROR)

        random.seed(1)
        np.random.seed(1)
        torch.manual_seed(1)

        self.num_node = 0
        self._static_topology_edges = []

        topology_file = os.path.join(
            TOPOLOGY_ROOT, topo_name, "Topology.txt")
        if load_topology_edges is not None and os.path.exists(topology_file):
            self._static_topology_edges = load_topology_edges(topology_file)
            node_ids = {
                endpoint
                for edge in self._static_topology_edges
                for endpoint in (edge["src"], edge["dst"])
            }
            self.num_node = len(node_ids)

        self.device = torch.device("cuda:0" if torch.cuda.is_available() else "cpu")
        self.gart_model = None
        self._last_model_action_used = False
        self._last_model_confidence = None

        gart_checkpoint = None
        if (
            os.path.isfile(self.model_path)
            and (
                self.algorithm_requested == "gart"
                or os.path.basename(self.model_path).lower() == "gart.pt"
            )
        ):
            gart_checkpoint = self.model_path
        elif os.path.isdir(self.model_path):
            candidate = os.path.join(self.model_path, "gart.pt")
            if os.path.exists(candidate):
                gart_checkpoint = candidate

        self.model_kind = "gart"

        if GARTActorCritic is None:
            print("[模型] GART 运行时不可用: %s" % GART_IMPORT_ERROR)
        elif not gart_checkpoint:
            print("[模型] 未找到 GART checkpoint (期望 gart.pt)，将回退 Dijkstra")
        else:
            try:
                checkpoint = torch.load(gart_checkpoint, map_location="cpu")
                self.gart_model = GARTActorCritic.from_checkpoint(checkpoint)
                self.gart_model.to(self.device)
                self.gart_model.eval()
                print("[模型] GART 模型已加载: %s" % gart_checkpoint)
            except Exception as exc:
                print("[模型] GART 加载失败: %s" % exc)
                self.gart_model = None

        print("[初始化] 完成！拓扑: %s, 节点数: %d, 模型: %s"
              % (topo_name, self.num_node, self.model_kind))

    def _sanitize_gart_path(self, path, src_node, dst_node, topo_edges):
        if not path or path[0] != src_node or path[-1] != dst_node:
            return None
        if len(path) != len(set(path)):
            return None
        available = set()
        for edge in topo_edges or []:
            try:
                if isinstance(edge, dict) and edge.get("status") == "down":
                    continue
                u, v, _ = _normalize_topo_edge(edge)
                available.add((u, v))
            except Exception:
                continue
        if any((u, v) not in available for u, v in zip(path[:-1], path[1:])):
            return None
        return path

    def compute_path_with_gart(self, src_node, dst_node, topo_edges,
                               deadline_ms=200.0):
        """Execute Algorithm 1 as decentralized per-hop next-hop decisions."""
        self._last_model_action_used = False
        self._last_model_confidence = None
        if self.gart_model is None or build_gart_observation is None:
            return None

        edges = topo_edges or self._static_topology_edges
        if not edges:
            return None

        path = [int(src_node)]
        current = int(src_node)
        confidences = []
        topology_index = GARTTopologyIndex(edges)
        max_hops = max(2 * len({
            endpoint
            for edge in edges
            for endpoint in (
                int(edge.get("src")) if isinstance(edge, dict) else int(edge[0]),
                int(edge.get("dst")) if isinstance(edge, dict) else int(edge[1]),
            )
        }), 1)

        try:
            for _ in range(max_hops):
                observation = build_gart_observation(
                    topology_index,
                    current_node=current,
                    destination_node=dst_node,
                    visited_nodes=path,
                    deadline_ms=deadline_ms,
                    max_deadline_ms=self.gart_model.config.max_deadline_ms,
                    neighborhood_hops=self.gart_model.config.gat_layers,
                )
                tensors = observation.to_tensors(self.device)
                with torch.no_grad():
                    _value, action, _log_probability, probabilities = self.gart_model.act(
                        tensors["node_features"],
                        tensors["adjacency"],
                        tensors["current_node"],
                        tensors["flow_features"],
                        tensors["action_mask"],
                        deterministic=True,
                    )
                action_index = int(action.item())
                next_node = observation.node_ids[action_index]
                confidence = float(probabilities[0, action_index].item())
                if next_node in path:
                    return None
                path.append(next_node)
                confidences.append(confidence)
                current = next_node
                if current == int(dst_node):
                    clean = self._sanitize_gart_path(
                        path, int(src_node), int(dst_node), edges)
                    if clean:
                        self._last_model_action_used = True
                        self._last_model_confidence = min(confidences) if confidences else 1.0
                    return clean
        except Exception as exc:
            print("[GART] 计算失败: %s" % exc)
            import traceback
            traceback.print_exc()
        return None

    def compute_path(self, src_node, dst_node, topo_edges=None, flow=None):
        """Compute a GART route and fall back to Dijkstra when needed."""
        flow = flow or {}
        edges = topo_edges or self._static_topology_edges
        deadline_ms = float(flow.get("deadline_ms", 200.0))

        if self.gart_model is not None:
            path = self.compute_path_with_gart(
                src_node, dst_node, edges, deadline_ms=deadline_ms)
            if path:
                print("[路径] GART 计算: %d -> %d = %s"
                      % (src_node, dst_node, path))
                return _decision(
                    "gart_model",
                    path,
                    model_used=True,
                    fallback_reason=None,
                    confidence=self._last_model_confidence,
                )

        if edges:
            path = _dijkstra_on_edges(edges, src_node, dst_node)
            if path:
                reason = (
                    "gart_failed"
                    if self.gart_model is not None
                    else "gart_model_not_loaded"
                )
                return _decision(
                    "dijkstra", path, model_used=False, fallback_reason=reason)

        return _decision(
            "none", None, model_used=False, fallback_reason="gart_no_path")

    def run(self):
        """Run the threaded TCP service."""
        s = socket.socket(socket.AF_INET, socket.SOCK_STREAM)
        s.setsockopt(socket.SOL_SOCKET, socket.SO_REUSEADDR, 1)
        s.bind(("127.0.0.1", self.port))
        s.listen(10)
        print("[服务] 已启动，监听端口 %d" % self.port)
        print("[服务] 等待控制器的路径计算请求...")
        print("[服务] 当前模型: %s" % self.model_kind)
        print("[服务] GART 使用控制器提供的动态拓扑和流截止期")

        def handle_client(conn, addr):
            """Handle multiple requests over one client connection."""
            buffer = ""
            try:
                while True:
                    data = conn.recv(65536)
                    if not data:
                        break
                    buffer += data.decode("utf-8")
                    while '\n' in buffer:
                        line, buffer = buffer.split('\n', 1)
                        line = line.strip()
                        if not line:
                            continue
                        try:
                            request = json.loads(line)
                        except json.JSONDecodeError as e:
                            print("[错误] JSON 解析失败: %s" % e)
                            continue

                        if request.get("type") == "path_request":
                            src_node = int(request["src_node"])
                            dst_node = int(request["dst_node"])
                            request_id = request.get("request_id")
                            topo_edges = request.get("topo_edges", None)
                            candidates = request.get("candidates") or []
                            route_mode = request.get("route_mode", "unknown")

                            print("[请求] %d -> %d (ID: %s, topo_edges: %s)"
                                  % (src_node, dst_node, request_id,
                                     "%d条" % len(topo_edges) if topo_edges else "无"))
                            print("[请求] route_mode=%s candidates=%d task=%s policy=%s"
                                  % (route_mode, len(candidates),
                                     request.get("task_type", "default"),
                                     request.get("route_policy", "shortest_path")))

                            start_time = time.time()
                            flow = {
                                "task_type": request.get("task_type", "default"),
                                "flow_type": request.get("flow_type", "RT"),
                                "deadline_ms": request.get("deadline_ms", 200.0),
                                "demand": request.get("demand", 100.0),
                            }
                            decision = self.compute_path(
                                src_node, dst_node, topo_edges, flow=flow)
                            elapsed = time.time() - start_time
                            path = decision.get("path") if isinstance(decision, dict) else decision

                            response = {
                                "type": "path_response",
                                "status": "ok" if path else "error",
                                "path": path,
                                "request_id": request_id,
                                "compute_time": elapsed,
                                "decision_source": decision.get("decision_source", "unknown"),
                                "model_used": decision.get("model_used", False),
                                "fallback_reason": decision.get("fallback_reason"),
                                "confidence": decision.get("confidence"),
                                "candidate_count": len(candidates),
                            }
                            if not path:
                                response["error"] = "no path"
                            print("[响应] 路径: %s (耗时: %.3fs)" % (path, elapsed))

                        elif request.get("type") == "batch_path_request":
                            requests = request.get("requests", [])
                            request_id = request.get("request_id")
                            topo_edges = request.get("topo_edges", None)

                            print("[批量请求] 共 %d 条路径 (ID: %s)" % (len(requests), request_id))

                            start_time = time.time()
                            paths = []
                            for req in requests:
                                src = int(req["src_node"])
                                dst = int(req["dst_node"])
                                decision = self.compute_path(
                                    src, dst, topo_edges, flow=req)
                                path = decision.get("path") if isinstance(decision, dict) else decision
                                paths.append({
                                    "src": src,
                                    "dst": dst,
                                    "path": path,
                                    "decision_source": decision.get("decision_source", "unknown"),
                                    "model_used": decision.get("model_used", False),
                                    "fallback_reason": decision.get("fallback_reason"),
                                    "confidence": decision.get("confidence"),
                                })
                            elapsed = time.time() - start_time

                            response = {
                                "type": "batch_path_response",
                                "status": "ok",
                                "paths": paths,
                                "request_id": request_id,
                                "compute_time": elapsed
                            }
                            print("[批量响应] 完成 %d 条路径 (耗时: %.3fs)" % (len(paths), elapsed))

                        else:
                            response = {
                                "type": "path_response",
                                "status": "error",
                                "error": "未知的请求类型",
                                "request_id": request.get("request_id"),
                            }

                        conn.send((json.dumps(response) + '\n').encode("utf-8"))
            except Exception as e:
                print("[错误] 处理连接失败: %s" % e)
                import traceback
                traceback.print_exc()
            finally:
                try:
                    conn.close()
                except:
                    pass
                print("[连接] 客户端断开: %s" % str(addr))

        while True:
            try:
                conn, addr = s.accept()
                client_thread = threading.Thread(target=handle_client, args=(conn, addr))
                client_thread.daemon = True
                client_thread.start()
            except Exception as e:
                print("[错误] 接受连接失败: %s" % e)
                import traceback
                traceback.print_exc()


DRLPathService = GARTPathService


if __name__ == "__main__":
    parser = argparse.ArgumentParser(description="GART 路径计算服务")
    parser.add_argument("--topo", default="nsfnet", help="拓扑名称")
    parser.add_argument("--port", type=int, default=8889, help="监听端口")
    parser.add_argument(
        "--model",
        default=None,
        help=("模型或 checkpoint 路径。相对路径按项目根目录解析；"
              "GART 默认使用 models/nsfnet/gart.pt"),
    )
    parser.add_argument(
        "--algorithm",
        choices=("auto", "gart"),
        default="gart",
        help="路由模型",
    )
    args = parser.parse_args()

    print("=" * 60)
    print("GART 路径计算服务")
    print("=" * 60)

    service = GARTPathService(args.topo, args.port, args.model, args.algorithm)
    try:
        service.run()
    except KeyboardInterrupt:
        print("\n[服务] 已停止")
