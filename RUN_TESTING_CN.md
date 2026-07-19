# GART 运行与测试说明

GART 默认提供 NSFNet、GEANT2、Renater 2010 和 Synthetic-300 四组拓扑。

## 1. 拓扑数据

| 数据集 | 节点 | 物理链路 | 有向链路 |
|---|---:|---:|---:|
| NSFNet | 14 | 21 | 42 |
| GEANT2 | 23 | 36 | 72 |
| Renater 2010 | 43 | 56 | 112 |
| Synthetic-300 | 300 | 669 | 1,338 |

每个 `topology/<数据集>/` 目录包含：

- `Topology.txt`：物理链路，加载时自动扩展为双向链路；
- `TM.txt`：可直接运行的确定性流量矩阵；
- `metadata.json`：数据来源、规模和归一化信息。

Synthetic-300 使用固定种子的度优先生成器。GEANT2 固定使用 36 条物理链路，
并在元数据中记录被排除的低容量非桥接边 `(6, 19)`。

## 2. 安装

```bash
pip3 install -r requirements.txt
```

完整网络仿真还需要在 Linux 中安装 Mininet 和 Open vSwitch。

## 3. 训练

默认训练 NSFNet：

```bash
python3 -m gart.train \
  --dataset nsfnet \
  --traffic-intensity 0.7 \
  --interactions 100000 \
  --seed 1
```

输出为 `models/nsfnet/gart.pt`。切换数据集示例：

```bash
python3 -m gart.train --dataset geant2 --traffic-intensity 0.3 --seed 1
python3 -m gart.train --dataset renater2010 --traffic-intensity 0.7 --seed 1
python3 -m gart.train --dataset synthetic300 --traffic-intensity 0.7 --seed 1
```

可通过不同随机种子和负载强度进行多轮评估；也可用 `--traffic-matrix`
传入自定义流量矩阵。

## 4. 启动服务与 Mininet

```bash
./start_suite.sh
```

默认启动 NSFNet。切换拓扑：

```bash
GART_TOPOLOGY=geant2 ./start_suite.sh
GART_TOPOLOGY=renater2010 ./start_suite.sh
```

默认模型路径为 `models/<拓扑名>/gart.pt`。模型不存在时，路径服务会回退到
Dijkstra 并记录原因。
通用 Mininet 启动器默认连接 Ryu 端口 6654；自定义测试床可通过
`CONTROLLER_PORTS=6654,6655` 指定多个控制器端口。

物理网卡混合模式：

```bash
GART_TOPOLOGY=nsfnet ./start_suite.sh eno1
```

## 5. 单独启动路径服务

```bash
python3 -m gart.path_service \
  --topo nsfnet \
  --algorithm gart \
  --model models/nsfnet/gart.pt
```

## 6. 验证

```bash
python3 -m pytest -q
python3 tools/build_topologies.py
git diff --exit-code -- topology
```

拓扑测试会检查节点连续性、连通性、重复链路、流量矩阵尺寸和目录元数据。

## 7. 停止与日志

```bash
./stop_suite.sh
cat logs/path_service.log
cat logs/server_agent.stdout.log
cat logs/controllers.log
```
