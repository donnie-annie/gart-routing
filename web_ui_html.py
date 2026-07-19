"""Embedded HTML, CSS, and JavaScript for the controller dashboard."""


def get_web_ui_html():
    html = '''
<!DOCTYPE html>
<html lang="zh-CN">
<head>
    <meta charset="UTF-8">
    <meta name="viewport" content="width=device-width, initial-scale=1.0">
    <title>Hierarchical SDN View - Root Controller</title>
    <script src="https://unpkg.com/vis-network@9.1.2/standalone/umd/vis-network.min.js"></script>
    <style>
        * {
            margin: 0;
            padding: 0;
            box-sizing: border-box;
        }
        body {
            font-family: -apple-system, BlinkMacSystemFont, 'Segoe UI', 'Roboto', 'Oxygen', 'Ubuntu', 'Cantarell', sans-serif;
            background: #020617;
            color: #e2e8f0;
            min-height: 100vh;
            overflow: hidden;
        }
        .app-container {
            display: flex;
            height: 100vh;
            overflow: hidden;
        }
        /* 顶部导航栏 */
        .header {
            position: fixed;
            top: 0;
            left: 0;
            right: 0;
            height: 64px;
            background: rgba(15, 23, 42, 0.8);
            backdrop-filter: blur(12px);
            border-bottom: 1px solid #1e293b;
            display: flex;
            align-items: center;
            justify-content: space-between;
            padding: 0 24px;
            z-index: 100;
        }
        .header-left {
            display: flex;
            align-items: center;
            gap: 16px;
        }
        .header-icon {
            background: #d97706;
            padding: 8px;
            border-radius: 8px;
            box-shadow: 0 4px 12px rgba(217, 119, 6, 0.3);
        }
        .header-icon svg {
            width: 24px;
            height: 24px;
            fill: white;
        }
        .header-title {
            font-size: 20px;
            font-weight: 700;
            color: #f1f5f9;
        }
        .header-title span {
            color: #f59e0b;
        }
        .header-status {
            display: flex;
            align-items: center;
            gap: 8px;
            font-size: 12px;
            color: #64748b;
        }
        .status-dot {
            width: 8px;
            height: 8px;
            border-radius: 50%;
            background: #22c55e;
            animation: pulse 2s infinite;
        }
        @keyframes pulse {
            0%, 100% { opacity: 1; }
            50% { opacity: 0.5; }
        }
        .header-metrics {
            display: flex;
            gap: 32px;
        }
        .header-controls {
            display: flex;
            align-items: center;
            gap: 14px;
            margin-left: 20px;
        }
        .compact-toggle {
            display: flex;
            align-items: center;
            gap: 8px;
            padding: 8px 12px;
            border: 1px solid rgba(51, 65, 85, 0.8);
            border-radius: 10px;
            background: rgba(15, 23, 42, 0.6);
            color: #cbd5e1;
            font-size: 12px;
            font-weight: 600;
            user-select: none;
        }
        .compact-toggle input {
            accent-color: #22d3ee;
            cursor: pointer;
        }
        .compact-toggle-label {
            cursor: pointer;
            white-space: nowrap;
        }
        .arrange-topology-btn {
            display: inline-flex;
            align-items: center;
            gap: 7px;
            border: 1px solid rgba(6, 182, 212, 0.45);
            border-radius: 8px;
            background: rgba(8, 145, 178, 0.16);
            color: #cffafe;
            font-size: 12px;
            font-weight: 700;
            padding: 8px 11px;
            cursor: pointer;
            transition: background 0.16s ease, border-color 0.16s ease, color 0.16s ease;
        }
        .arrange-topology-btn:hover {
            background: rgba(8, 145, 178, 0.28);
            border-color: rgba(34, 211, 238, 0.75);
            color: #ecfeff;
        }
        .arrange-topology-btn svg {
            width: 14px;
            height: 14px;
        }
        .metric-box {
            display: flex;
            align-items: center;
            gap: 12px;
            background: rgba(30, 41, 59, 0.5);
            padding: 8px 16px;
            border-radius: 8px;
            border: 1px solid rgba(51, 65, 85, 0.5);
        }
        .metric-icon {
            width: 16px;
            height: 16px;
        }
        .metric-content {
            display: flex;
            flex-direction: column;
        }
        .metric-label {
            font-size: 10px;
            color: #64748b;
            text-transform: uppercase;
            font-weight: 700;
            letter-spacing: 0.5px;
        }
        .metric-value {
            font-size: 14px;
            font-family: monospace;
            font-weight: 700;
            color: #e2e8f0;
        }
        /* 主内容区域 */
        .main-content {
            flex: 1;
            display: flex;
            flex-direction: column;
            margin-top: 64px;
            position: relative;
        }
        /* 拓扑图区域 */
        .topology-area {
            flex: 1;
            position: relative;
            background: #020617;
            overflow: hidden;
            background-image: radial-gradient(#334155 1px, transparent 1px);
            background-size: 30px 30px;
        }
        #network {
            width: 100%;
            height: 100%;
        }
        .route-sessions-panel {
            position: absolute;
            top: 16px;
            left: 16px;
            width: 360px;
            max-height: calc(100% - 32px);
            display: none;
            flex-direction: column;
            background: rgba(2, 6, 23, 0.88);
            border: 1px solid rgba(51, 65, 85, 0.9);
            border-radius: 12px;
            box-shadow: 0 8px 24px rgba(2, 6, 23, 0.6);
            backdrop-filter: blur(8px);
            z-index: 40;
            overflow: hidden;
        }
        .route-sessions-panel.visible {
            display: flex;
        }
        .route-sessions-header {
            padding: 12px 14px;
            border-bottom: 1px solid rgba(51, 65, 85, 0.8);
            display: flex;
            align-items: center;
            justify-content: space-between;
            gap: 10px;
        }
        .route-sessions-title {
            font-size: 12px;
            font-weight: 700;
            letter-spacing: 0.7px;
            text-transform: uppercase;
            color: #67e8f9;
        }
        .route-sessions-count {
            font-size: 11px;
            color: #94a3b8;
            font-family: monospace;
        }
        .route-sessions-list {
            overflow-y: auto;
            padding: 8px;
            display: flex;
            flex-direction: column;
            gap: 6px;
        }
        .route-session-item {
            border: 1px solid rgba(51, 65, 85, 0.7);
            border-radius: 8px;
            padding: 10px 10px;
            background: rgba(15, 23, 42, 0.72);
            cursor: pointer;
            transition: border-color 0.2s ease, background 0.2s ease, transform 0.15s ease;
        }
        .route-session-item:hover {
            border-color: rgba(34, 211, 238, 0.8);
            background: rgba(15, 23, 42, 0.92);
            transform: translateY(-1px);
        }
        .route-session-item.active {
            border-color: #f59e0b;
            background: rgba(120, 53, 15, 0.28);
            box-shadow: 0 0 0 1px rgba(251, 191, 36, 0.35) inset;
        }
        .route-session-path {
            font-family: monospace;
            font-size: 12px;
            color: #e2e8f0;
            line-height: 1.5;
            word-break: break-all;
        }
        .route-session-meta {
            margin-top: 4px;
            font-family: monospace;
            font-size: 11px;
            color: #94a3b8;
            line-height: 1.4;
            word-break: break-word;
        }
        .route-session-empty {
            padding: 20px 12px;
            color: #64748b;
            font-size: 12px;
            text-align: center;
        }
        .route-sessions-actions {
            padding: 8px 12px 12px;
            border-top: 1px solid rgba(51, 65, 85, 0.6);
            display: flex;
            justify-content: flex-end;
        }
        .route-sessions-clear-btn {
            border: 1px solid rgba(100, 116, 139, 0.9);
            background: transparent;
            color: #cbd5e1;
            border-radius: 8px;
            padding: 6px 10px;
            font-size: 12px;
            cursor: pointer;
        }
        .route-sessions-clear-btn:hover {
            border-color: rgba(34, 211, 238, 0.9);
            color: #e2e8f0;
        }
        /* 右侧信息面板 */
        .sidebar {
            width: 420px;
            background: #0f172a;
            border-left: 1px solid #1e293b;
            display: flex;
            flex-direction: column;
            box-shadow: -4px 0 24px rgba(0, 0, 0, 0.3);
            z-index: 50;
            margin-top: 64px;
            height: calc(100vh - 64px);
        }
        .sidebar-header {
            padding: 24px;
            border-bottom: 1px solid #1e293b;
            background: rgba(30, 41, 59, 0.3);
            display: flex;
            justify-content: space-between;
            align-items: start;
        }
        .sidebar-title-group {
            display: flex;
            align-items: center;
            gap: 12px;
        }
        .sidebar-icon {
            padding: 8px;
            border-radius: 8px;
        }
        .sidebar-icon.root { background: rgba(217, 119, 6, 0.2); color: #f59e0b; }
        .sidebar-icon.controller { background: rgba(59, 130, 246, 0.2); color: #60a5fa; }
        .sidebar-icon.switch { background: rgba(6, 182, 212, 0.2); color: #22d3ee; }
        .sidebar-icon.host { background: rgba(51, 65, 85, 0.2); color: #94a3b8; }
        .sidebar-title {
            font-size: 18px;
            font-weight: 700;
            color: white;
        }
        .sidebar-subtitle {
            font-size: 12px;
            color: #64748b;
            font-family: monospace;
            margin-top: 4px;
        }
        .sidebar-close {
            color: #64748b;
            cursor: pointer;
            padding: 4px;
            border-radius: 4px;
            transition: all 0.2s;
        }
        .sidebar-close:hover {
            color: white;
            background: #1e293b;
        }
        .sidebar-content {
            flex: 1;
            overflow-y: auto;
            padding: 24px;
        }
        .sidebar-section {
            margin-bottom: 32px;
        }
        .section-title {
            font-size: 12px;
            font-weight: 700;
            color: #64748b;
            text-transform: uppercase;
            letter-spacing: 1px;
            margin-bottom: 12px;
        }
        .info-card {
            background: rgba(30, 41, 59, 0.5);
            border-radius: 12px;
            padding: 16px;
            border: 1px solid rgba(51, 65, 85, 0.5);
        }
        .info-row {
            display: flex;
            justify-content: space-between;
            align-items: center;
            font-size: 14px;
            margin-bottom: 12px;
        }
        .info-row:last-child {
            margin-bottom: 0;
        }
        .info-label {
            color: #94a3b8;
        }
        .info-value {
            font-family: monospace;
            color: #e2e8f0;
            font-weight: 500;
        }
        .info-value.highlight {
            background: rgba(51, 65, 85, 0.5);
            padding: 4px 8px;
            border-radius: 4px;
            font-weight: 700;
        }
        .info-value.error {
            color: #f87171;
        }
        .divider {
            height: 1px;
            background: rgba(51, 65, 85, 0.5);
            margin: 12px 0;
        }
        .empty-state {
            text-align: center;
            color: #64748b;
            margin-top: 80px;
        }
        .empty-state-icon {
            width: 64px;
            height: 64px;
            margin: 0 auto 16px;
            opacity: 0.2;
        }
        .flow-table {
            min-height: 200px;
        }
        .flow-item {
            background: rgba(30, 41, 59, 0.5);
            border: 1px solid rgba(51, 65, 85, 0.6);
            border-radius: 8px;
            padding: 14px;
            margin-bottom: 12px;
            transition: all 0.2s;
        }
        .flow-item:hover {
            border-color: rgba(59, 130, 246, 0.5);
        }
        .flow-header {
            display: flex;
            justify-content: space-between;
            align-items: start;
            margin-bottom: 10px;
        }
        .flow-priority {
            background: rgba(51, 65, 85, 0.5);
            padding: 4px 8px;
            border-radius: 4px;
            font-size: 10px;
            font-family: monospace;
            color: #cbd5e0;
            border: 1px solid rgba(51, 65, 85, 0.3);
        }
        .flow-status {
            width: 6px;
            height: 6px;
            border-radius: 50%;
            background: #22c55e;
            box-shadow: 0 0 5px rgba(34, 197, 94, 0.6);
        }
        .flow-delete {
            color: #64748b;
            cursor: pointer;
            padding: 4px;
            border-radius: 4px;
            opacity: 0;
            transition: all 0.2s;
        }
        .flow-item:hover .flow-delete {
            opacity: 1;
        }
        .flow-delete:hover {
            color: #f87171;
            background: rgba(51, 65, 85, 0.5);
        }
        .flow-details {
            display: flex;
            flex-direction: column;
            gap: 6px;
        }
        .flow-detail-row {
            display: flex;
            gap: 8px;
            font-size: 12px;
        }
        .flow-detail-label {
            color: #64748b;
            font-weight: 500;
            width: 40px;
        }
        .flow-detail-value {
            font-family: monospace;
            flex: 1;
            overflow: hidden;
            text-overflow: ellipsis;
        }
        .flow-detail-value.match {
            color: #fbbf24;
        }
        .flow-detail-value.action {
            color: #22d3ee;
        }
        .flow-footer {
            margin-top: 12px;
            padding-top: 8px;
            border-top: 1px solid rgba(51, 65, 85, 0.3);
            display: flex;
            justify-content: space-between;
            align-items: center;
            font-size: 10px;
            color: #64748b;
        }
        .flow-packet-count {
            display: flex;
            align-items: center;
            gap: 4px;
            font-family: monospace;
            background: rgba(15, 23, 42, 0.3);
            padding: 4px 6px;
            border-radius: 4px;
        }
        .btn-add-flow {
            font-size: 12px;
            background: #2563eb;
            color: white;
            padding: 6px 12px;
            border-radius: 6px;
            border: none;
            cursor: pointer;
            display: flex;
            align-items: center;
            gap: 6px;
            transition: all 0.2s;
            box-shadow: 0 4px 12px rgba(37, 99, 235, 0.2);
        }
        .btn-add-flow:hover {
            background: #1d4ed8;
            transform: scale(0.98);
        }
        .btn-add-flow:active {
            transform: scale(0.95);
        }
        .flow-modal-overlay {
            position: fixed;
            inset: 0;
            background: rgba(2, 6, 23, 0.75);
            backdrop-filter: blur(4px);
            display: none;
            align-items: center;
            justify-content: center;
            z-index: 200;
            padding: 20px;
        }
        .flow-modal {
            width: min(760px, 95vw);
            max-height: 90vh;
            overflow-y: auto;
            background: #0f172a;
            border: 1px solid #334155;
            border-radius: 12px;
            box-shadow: 0 24px 48px rgba(0, 0, 0, 0.45);
            padding: 18px;
        }
        .flow-modal-header {
            display: flex;
            justify-content: space-between;
            align-items: center;
            margin-bottom: 12px;
        }
        .flow-modal-title {
            font-size: 16px;
            font-weight: 700;
            color: #f1f5f9;
        }
        .flow-modal-subtitle {
            font-size: 12px;
            color: #94a3b8;
            font-family: monospace;
            margin-top: 4px;
        }
        .flow-modal-close {
            border: none;
            background: transparent;
            color: #94a3b8;
            cursor: pointer;
            font-size: 20px;
            line-height: 1;
            padding: 4px 8px;
            border-radius: 6px;
        }
        .flow-modal-close:hover {
            color: #f8fafc;
            background: rgba(51, 65, 85, 0.5);
        }
        .flow-form-grid {
            display: grid;
            grid-template-columns: repeat(2, minmax(0, 1fr));
            gap: 10px;
        }
        .flow-form-field {
            display: flex;
            flex-direction: column;
            gap: 6px;
        }
        .flow-form-field label {
            font-size: 12px;
            color: #cbd5e1;
        }
        .flow-form-field input, .flow-form-field select, .flow-match-preview {
            width: 100%;
            border: 1px solid #334155;
            background: #020617;
            color: #e2e8f0;
            border-radius: 8px;
            padding: 8px 10px;
            font-size: 13px;
        }
        .flow-form-field input:focus, .flow-form-field select:focus, .flow-match-preview:focus {
            outline: none;
            border-color: #3b82f6;
            box-shadow: 0 0 0 2px rgba(59, 130, 246, 0.2);
        }
        .flow-form-tip {
            font-size: 11px;
            color: #64748b;
        }
        .flow-form-full {
            grid-column: 1 / -1;
        }
        .flow-match-preview {
            min-height: 130px;
            font-family: ui-monospace, SFMono-Regular, Menlo, Monaco, Consolas, monospace;
            resize: vertical;
        }
        .flow-form-error {
            margin-top: 10px;
            padding: 8px 10px;
            border-radius: 8px;
            background: rgba(239, 68, 68, 0.15);
            border: 1px solid rgba(248, 113, 113, 0.35);
            color: #fca5a5;
            font-size: 12px;
            display: none;
        }
        .flow-form-actions {
            margin-top: 14px;
            display: flex;
            justify-content: flex-end;
            gap: 10px;
        }
        .btn-secondary {
            border: 1px solid #334155;
            background: transparent;
            color: #cbd5e1;
            border-radius: 8px;
            padding: 8px 12px;
            cursor: pointer;
        }
        .btn-secondary:hover {
            background: rgba(51, 65, 85, 0.4);
        }
        .btn-primary {
            border: none;
            background: #2563eb;
            color: #fff;
            border-radius: 8px;
            padding: 8px 14px;
            cursor: pointer;
        }
        .btn-primary:hover {
            background: #1d4ed8;
        }
    </style>
</head>
<body>
    <div class="app-container">
        <!-- 顶部导航栏 -->
        <header class="header">
            <div class="header-left">
                <div class="header-icon">
                    <svg viewBox="0 0 24 24" fill="currentColor">
                        <circle cx="12" cy="12" r="10"/>
                        <path d="M12 2L2 7l10 5 10-5-10-5zM2 17l10 5 10-5M2 12l10 5 10-5"/>
                    </svg>
                </div>
                <div>
                    <h1 class="header-title">Hierarchical <span>SDN View</span></h1>
                    <div class="header-status">
                        <span class="status-dot"></span>
                        System Healthy
                </div>
                </div>
                </div>
            <div class="header-metrics">
                <div class="metric-box">
                    <svg class="metric-icon" viewBox="0 0 24 24" fill="none" stroke="currentColor" stroke-width="2">
                        <polyline points="22 12 18 12 15 21 9 3 6 12 2 12"/>
                    </svg>
                    <div class="metric-content">
                        <span class="metric-label">Global Throughput</span>
                        <span class="metric-value" id="metric-throughput">0 Mbps</span>
            </div>
        </div>
                <div class="metric-box">
                    <svg class="metric-icon" viewBox="0 0 24 24" fill="none" stroke="currentColor" stroke-width="2">
                        <polyline points="13 2 3 14 12 14 11 22 21 10 12 10 13 2"/>
                    </svg>
                    <div class="metric-content">
                        <span class="metric-label">Avg Latency</span>
                        <span class="metric-value" id="metric-latency">0 ms</span>
            </div>
                </div>
                <div class="header-controls">
                    <button type="button" class="arrange-topology-btn" onclick="arrangeTopology()" title="清除拖拽坐标并重新整理拓扑">
                        <svg viewBox="0 0 24 24" fill="none" stroke="currentColor" stroke-width="2">
                            <path d="M3 6h18"/>
                            <path d="M7 12h10"/>
                            <path d="M10 18h4"/>
                        </svg>
                        <span>整理拓扑</span>
                    </button>
                    <label class="compact-toggle" for="compact-mode-toggle">
                        <input id="compact-mode-toggle" type="checkbox" checked disabled />
                        <span class="compact-toggle-label">精简模式（调试中，已锁定）</span>
                    </label>
                </div>
            </div>
        </header>

        <!-- 主内容区域 -->
        <div class="main-content">
            <!-- 拓扑图区域 -->
            <div class="topology-area">
            <div class="route-sessions-panel" id="route-sessions-panel">
                <div class="route-sessions-header">
                    <div class="route-sessions-title">Route Sessions</div>
                    <div class="route-sessions-count" id="route-sessions-count">0</div>
                </div>
                <div class="route-sessions-list" id="route-sessions-list"></div>
                <div class="route-sessions-actions">
                    <button type="button" class="route-sessions-clear-btn" onclick="clearRouteSessionSelection()">取消高亮</button>
                </div>
            </div>
            <div id="network"></div>
            </div>
        </div>

        <!-- 右侧信息面板 -->
        <div class="sidebar" id="sidebar">
            <div class="sidebar-header">
                <div class="sidebar-title-group">
                    <div class="sidebar-icon" id="sidebar-icon">
                        <svg width="24" height="24" viewBox="0 0 24 24" fill="none" stroke="currentColor" stroke-width="2">
                            <circle cx="12" cy="12" r="10"/>
                        </svg>
                </div>
                    <div>
                        <h2 class="sidebar-title" id="sidebar-title">Select Node</h2>
                        <p class="sidebar-subtitle" id="sidebar-subtitle">Click a node to view details</p>
                </div>
                </div>
                <div class="sidebar-close" onclick="closeSidebar()">
                    <svg width="20" height="20" viewBox="0 0 24 24" fill="none" stroke="currentColor" stroke-width="2">
                        <line x1="18" y1="6" x2="6" y2="18"/>
                        <line x1="6" y1="6" x2="18" y2="18"/>
                    </svg>
                </div>
            </div>
            <div class="sidebar-content" id="sidebar-content">
                <div class="empty-state">
                    <svg class="empty-state-icon" viewBox="0 0 24 24" fill="none" stroke="currentColor" stroke-width="2">
                        <circle cx="12" cy="12" r="10"/>
                        <line x1="12" y1="8" x2="12" y2="12"/>
                        <line x1="12" y1="16" x2="12.01" y2="16"/>
                    </svg>
                    <p>Select a node from the topology</p>
                </div>
            </div>
        </div>
    </div>
    <div class="flow-modal-overlay" id="flow-modal-overlay">
        <div class="flow-modal">
            <div class="flow-modal-header">
                <div>
                    <div class="flow-modal-title">手动下发流表</div>
                    <div class="flow-modal-subtitle" id="flow-modal-switch-id">交换机: -</div>
                </div>
                <button class="flow-modal-close" type="button" onclick="closeAddFlowModal()">&times;</button>
            </div>
            <form onsubmit="handleAddFlowSubmit(event)">
                <div class="flow-form-grid">
                    <div class="flow-form-field">
                        <label for="flow-out-port">输出端口 out_port *</label>
                        <input id="flow-out-port" type="number" min="1" step="1" placeholder="例如 3" required />
                    </div>
                    <div class="flow-form-field">
                        <label for="flow-priority">优先级 priority</label>
                        <input id="flow-priority" type="number" min="0" step="1" value="10" />
                    </div>
                    <div class="flow-form-field">
                        <label for="flow-idle-timeout">空闲超时 idle_timeout</label>
                        <input id="flow-idle-timeout" type="number" min="0" step="1" value="0" />
                    </div>
                    <div class="flow-form-field">
                        <label for="flow-hard-timeout">硬超时 hard_timeout</label>
                        <input id="flow-hard-timeout" type="number" min="0" step="1" value="0" />
                    </div>
                    <div class="flow-form-field">
                        <label for="flow-in-port">入端口 in_port</label>
                        <input id="flow-in-port" type="number" min="1" step="1" placeholder="可选" />
                    </div>
                    <div class="flow-form-field">
                        <label for="flow-ip-proto">IP 协议 ip_proto</label>
                        <select id="flow-ip-proto">
                            <option value="">不限制</option>
                            <option value="6">TCP (6)</option>
                            <option value="17">UDP (17)</option>
                        </select>
                    </div>
                    <div class="flow-form-field">
                        <label for="flow-ipv4-src">源 IP ipv4_src</label>
                        <input id="flow-ipv4-src" type="text" placeholder="例如 10.0.0.1" />
                    </div>
                    <div class="flow-form-field">
                        <label for="flow-ipv4-dst">目的 IP ipv4_dst</label>
                        <input id="flow-ipv4-dst" type="text" placeholder="例如 10.0.0.2" />
                    </div>
                    <div class="flow-form-field">
                        <label for="flow-l4-src">L4 源端口</label>
                        <input id="flow-l4-src" type="number" min="1" max="65535" step="1" placeholder="可选" />
                    </div>
                    <div class="flow-form-field">
                        <label for="flow-l4-dst">L4 目的端口</label>
                        <input id="flow-l4-dst" type="number" min="1" max="65535" step="1" placeholder="可选" />
                    </div>
                    <div class="flow-form-field flow-form-full">
                        <label for="flow-match-json">Match 预览（可编辑 JSON）</label>
                        <textarea id="flow-match-json" class="flow-match-preview"></textarea>
                        <div class="flow-form-tip">点击“根据字段生成”可刷新 JSON；提交时会以这里的 JSON 为准。</div>
                    </div>
                </div>
                <div class="flow-form-error" id="flow-form-error"></div>
                <div class="flow-form-actions">
                    <button type="button" class="btn-secondary" onclick="populateMatchPreviewFromFields()">根据字段生成</button>
                    <button type="button" class="btn-secondary" onclick="closeAddFlowModal()">取消</button>
                    <button type="submit" class="btn-primary">提交下发</button>
                </div>
            </form>
        </div>
    </div>

    <script>
        let network = null;
        let nodes = null;
        let edges = null;
        let currentSelectedSwitchId = null;
        // 调试阶段：前端仅保留精简模式，普通模式逻辑暂时停用。
        let compactModeEnabled = true;
        let currentSwitchDomainMap = {};
        let domainRegions = [];
        let switchManualPositions = {};
        let lastCompactLayoutData = null;
        let routeSessions = [];
        let selectedRouteSessionId = null;
        let selectedRouteSessionSignature = null;
        let isRefreshInFlight = false;
        let lastGraphSignature = null;
        let lastTopologySignature = null;
        let lastLayoutSignature = null;
        let lastHighlightedNodeIds = new Set();
        let lastHighlightedEdgeIds = new Set();
        let switchLinkEdgeIdsByKey = new Map();
        let graphNodeIdsByKey = new Map();
        let graphNodeDataById = new Map();
        let graphEdgeDataById = new Map();
        let hoveredEdgeId = null;
        let hasAutoFitInitialTopology = false;
        const WEB_DEBUG = false;
        const compactModeStorageKey = 'hydrateCompactModeEnabled';
        const compactPositionStorageKey = 'hydrateCompactSwitchPositions';
        const domainRegionColors = [
            'rgba(8, 47, 73, 0.35)',
            'rgba(30, 58, 138, 0.32)',
            'rgba(6, 78, 59, 0.34)',
            'rgba(88, 28, 135, 0.30)',
            'rgba(113, 63, 18, 0.32)',
            'rgba(15, 118, 110, 0.32)'
        ];

        // 交换机链路断开：闪烁提示（3s）相关
        let linkRemovalBlinkTimers = {};

        function debugLog() {
            if (WEB_DEBUG && window.console && console.log) {
                console.log.apply(console, arguments);
            }
        }

        function canonicalSwitchLinkKey(a, b) {
            const x = String(a), y = String(b);
            return (x <= y) ? (x + '||' + y) : (y + '||' + x);
        }

        function normalizeSwitchId(v) {
            return String(v);
        }

        function getStableNodeNumber(nodeId) {
            const text = String(nodeId);
            const match = text.match(/([0-9]+)$/);
            if (!match) return text;
            const n = Number(match[1]);
            return Number.isFinite(n) ? n : text;
        }

        function formatSwitchLabel(nodeId) {
            return 'SW' + String(getStableNodeNumber(nodeId));
        }

        function formatHostLabel(nodeId, nodeData) {
            const ip = nodeData && nodeData.ip ? nodeData.ip : String(nodeId);
            const match = String(ip).match(/([0-9]+)$/);
            return match ? ('H' + match[1]) : String(ip);
        }

        function getNodeDisplayLabel(node) {
            if (!node) return '';
            if (node.nodeType === 'switch') return formatSwitchLabel(node.id);
            if (node.nodeType === 'host') return formatHostLabel(node.id, node.nodeData || {});
            return node.label || String(node.id);
        }

        function formatEndpointLabel(node, fallbackId) {
            if (node) return getNodeDisplayLabel(node);
            return formatSwitchLabel(fallbackId);
        }

        function formatRouteSessionPath(item) {
            if (!item) return '';
            const switchPath = Array.isArray(item.switch_path) ? item.switch_path : [];
            if (!switchPath.length) return item.display_path || '';
            const parts = [];
            if (item.src_ip) parts.push('Host(' + item.src_ip + ')');
            switchPath.forEach((switchId) => {
                parts.push(formatSwitchLabel(switchId));
            });
            if (item.dst_ip) parts.push('Host(' + item.dst_ip + ')');
            return parts.join(' -> ');
        }

        function sanitizeHtml(text) {
            return String(text)
                .replace(/&/g, '&amp;')
                .replace(/</g, '&lt;')
                .replace(/>/g, '&gt;')
                .replace(/"/g, '&quot;')
                .replace(/'/g, '&#39;');
        }

        function getActiveRouteSession() {
            if (!selectedRouteSessionId) return null;
            return routeSessions.find((item) => item && item.id === selectedRouteSessionId) || null;
        }

        function getRouteSessionSignature(item) {
            if (!item) return '';
            const l4 = item.l4_match ? JSON.stringify(item.l4_match) : '';
            return [
                item.src_ip || '',
                item.dst_ip || '',
                item.task_type || 'default',
                item.route_policy || 'shortest_path',
                l4
            ].join('|');
        }

        function computeGraphSignature(data) {
            const nodeParts = (data.nodes || []).map((item) => {
                const nodeData = item.data || {};
                return [
                    String(item.id),
                    nodeData.node_type || '',
                    nodeData.gateway_ip || ''
                ].join(':');
            }).sort();
            const edgeParts = (data.edges || []).map((item) => {
                const edgeData = item.data || {};
                return [
                    String(item.source),
                    String(item.target),
                    edgeData.edge_type || '',
                    edgeData.status || ''
                ].join(':');
            }).sort();
            return JSON.stringify({ nodes: nodeParts, edges: edgeParts });
        }

        function computeTopologySignature(data) {
            const nodeParts = (data.nodes || []).map((item) => {
                const nodeData = item.data || {};
                return [
                    String(item.id),
                    nodeData.node_type || '',
                    nodeData.gateway_ip || ''
                ].join(':');
            }).sort();
            const edgeParts = (data.edges || []).map((item) => {
                const edgeData = item.data || {};
                return [
                    String(item.source),
                    String(item.target),
                    edgeData.edge_type || '',
                    edgeData.status || ''
                ].join(':');
            }).sort();
            return JSON.stringify({ nodes: nodeParts, edges: edgeParts });
        }

        function syncDataSet(dataSet, desiredItems) {
            const desiredIds = new Set(desiredItems.map((item) => String(item.id)));
            const currentIds = dataSet.getIds();
            const toRemove = currentIds.filter((id) => {
                const key = String(id);
                return !desiredIds.has(key) && !key.startsWith('phantom-sl-');
            });
            const toAdd = [];
            const toUpdate = [];

            desiredItems.forEach((item) => {
                if (dataSet.get(item.id)) {
                    toUpdate.push(item);
                } else {
                    toAdd.push(item);
                }
            });

            if (toRemove.length) dataSet.remove(toRemove);
            if (toUpdate.length) dataSet.update(toUpdate);
            if (toAdd.length) dataSet.add(toAdd);
        }

        function stableEdgeId(edgeType, source, target) {
            const type = edgeType || 'unknown';
            const pair = type === 'switch_link'
                ? canonicalSwitchLinkKey(source, target)
                : (String(source) + '||' + String(target));
            return [
                'edge',
                type,
                pair
            ].join('|');
        }

        function fitInitialTopologyOnce() {
            if (hasAutoFitInitialTopology || !network) return;
            hasAutoFitInitialTopology = true;
            setTimeout(() => {
                fitTopologyView(500);
            }, 100);
        }

        function arrangeTopology() {
            if (!network || !nodes || !lastCompactLayoutData) return;
            switchManualPositions = {};
            try {
                localStorage.removeItem(compactPositionStorageKey);
            } catch (err) {}
            lastLayoutSignature = null;
            currentSwitchDomainMap = lastCompactLayoutData.switchDomainMap || {};
            applyCompactLayout(lastCompactLayoutData.nodes, currentSwitchDomainMap, lastCompactLayoutData.edges);
            persistCompactPreferences();
            applyRouteSessionHighlight();
            fitTopologyView(550);
        }

        function refreshGraphMetadataCache(data) {
            const graphNodes = data.nodes || [];
            const graphEdges = data.edges || [];
            const renderData = buildCompactGraphData(graphNodes, graphEdges);
            const nextNodeIds = new Map();
            const nextNodeData = new Map();
            const nextEdgeData = new Map();
            const nextSwitchLinkEdgeIdsByKey = new Map();

            (renderData.nodes || []).forEach((nodeObj) => {
                const nodeId = nodeObj.id || nodeObj;
                nextNodeIds.set(String(nodeId), nodeId);
                nextNodeData.set(String(nodeId), Object.assign({}, nodeObj.data || {}));
            });

            (renderData.edges || []).forEach((edgeObj) => {
                const source = edgeObj.source;
                const target = edgeObj.target;
                const edgeData = Object.assign({}, edgeObj.data || {});
                const edgeType = edgeData.edge_type || 'unknown';
                const sourceDomain = (renderData.switchDomainMap || {})[String(source)] || 'Domain-Unknown';
                const targetDomain = (renderData.switchDomainMap || {})[String(target)] || 'Domain-Unknown';
                edgeData.edge_type = edgeType;
                edgeData.inter_domain = sourceDomain !== targetDomain;
                edgeData.source_domain = sourceDomain;
                edgeData.target_domain = targetDomain;
                const edgeId = stableEdgeId(edgeType, source, target);
                nextEdgeData.set(edgeId, edgeData);
                if (edgeType === 'switch_link') {
                    const linkKey = canonicalSwitchLinkKey(source, target);
                    if (!nextSwitchLinkEdgeIdsByKey.has(linkKey)) {
                        nextSwitchLinkEdgeIdsByKey.set(linkKey, []);
                    }
                    nextSwitchLinkEdgeIdsByKey.get(linkKey).push(edgeId);
                }
            });

            graphNodeIdsByKey = nextNodeIds;
            graphNodeDataById = nextNodeData;
            graphEdgeDataById = nextEdgeData;
            switchLinkEdgeIdsByKey = nextSwitchLinkEdgeIdsByKey;
        }

        function getVisNodeId(nodeId) {
            const key = String(nodeId);
            return graphNodeIdsByKey.has(key) ? graphNodeIdsByKey.get(key) : nodeId;
        }

        function getNodeMetadata(nodeId, fallbackNode) {
            const cached = graphNodeDataById.get(String(nodeId));
            const fallback = (fallbackNode && fallbackNode.nodeData) || {};
            if (!cached) return fallback;
            const merged = Object.assign({}, fallback, cached);
            if (Array.isArray(fallback.flow_table)) merged.flow_table = fallback.flow_table;
            if (fallback.flow_table_error) merged.flow_table_error = fallback.flow_table_error;
            return merged;
        }

        function getEdgeMetadata(edgeId, fallbackEdge) {
            const cached = graphEdgeDataById.get(String(edgeId));
            return cached || ((fallbackEdge && fallbackEdge.data) || {});
        }

        function buildSwitchLinkKeySetFromPath(path) {
            const keys = new Set();
            const arr = Array.isArray(path) ? path.map((x) => String(x)) : [];
            for (let i = 0; i < arr.length - 1; i++) {
                keys.add(canonicalSwitchLinkKey(arr[i], arr[i + 1]));
            }
            return keys;
        }

        function updateRouteSessionsPanel() {
            const panel = document.getElementById('route-sessions-panel');
            const listEl = document.getElementById('route-sessions-list');
            const countEl = document.getElementById('route-sessions-count');
            if (!panel || !listEl || !countEl) return;

            if (!compactModeEnabled) {
                panel.classList.remove('visible');
                return;
            }
            panel.classList.add('visible');
            countEl.textContent = String(routeSessions.length);

            if (!routeSessions.length) {
                listEl.innerHTML = '<div class="route-session-empty">暂无路径会话</div>';
                return;
            }

            const html = routeSessions.map((item) => {
                const activeClass = item.id === selectedRouteSessionId ? ' active' : '';
                const pathText = formatRouteSessionPath(item);
                const source = item.decision_source || item.path_source || 'unknown';
                const modelUsed = item.model_used ? 'model' : 'fallback';
                const reason = item.fallback_reason || '';
                const decisionText = source + ' / ' + modelUsed + (reason ? ' / ' + reason : '');
                return (
                    '<div class="route-session-item' + activeClass + '" data-session-id="' + sanitizeHtml(item.id) + '">' +
                        '<div class="route-session-path">' + sanitizeHtml(pathText || '-') + '</div>' +
                        '<div class="route-session-meta">' + sanitizeHtml(decisionText) + '</div>' +
                    '</div>'
                );
            }).join('');
            listEl.innerHTML = html;
        }

        function applyRouteSessionHighlight() {
            if (!nodes || !edges) return;
            const active = getActiveRouteSession();
            const currentNodeIds = new Set();
            const currentEdgeIds = new Set();

            if (active) {
                const switchPath = Array.isArray(active.switch_path) ? active.switch_path.map((x) => String(x)) : [];
                switchPath.forEach((nodeId) => currentNodeIds.add(getVisNodeId(nodeId)));
                buildSwitchLinkKeySetFromPath(switchPath).forEach((linkKey) => {
                    const edgeIds = switchLinkEdgeIdsByKey.get(linkKey) || [];
                    edgeIds.forEach((edgeId) => currentEdgeIds.add(edgeId));
                });
            }

            lastHighlightedNodeIds.forEach((nodeId) => {
                if (currentNodeIds.has(nodeId)) return;
                const node = nodes.get(nodeId);
                if (!node) return;
                const update = { id: node.id };
                if (node.originalColor) update.color = node.originalColor;
                if (typeof node.originalSize === 'number') update.size = node.originalSize;
                if (typeof node.originalBorderWidth === 'number') update.borderWidth = node.originalBorderWidth;
                if (node.originalShadow !== undefined) update.shadow = node.originalShadow;
                nodes.update(update);
            });

            currentNodeIds.forEach((nodeId) => {
                const node = nodes.get(nodeId);
                if (!node) return;
                nodes.update({
                    id: node.id,
                    color: {
                        background: '#ecfeff',
                        border: '#06b6d4',
                        highlight: { background: '#cffafe', border: '#22d3ee' },
                        hover: { background: '#cffafe', border: '#22d3ee' }
                    },
                    borderWidth: 5,
                    shadow: {
                        enabled: true,
                        color: 'rgba(6, 182, 212, 0.85)',
                        size: 24,
                        x: 0,
                        y: 0
                    },
                    size: Math.max((node.originalSize || node.size || 30) + 7, 43)
                });
            });

            lastHighlightedEdgeIds.forEach((edgeId) => {
                if (currentEdgeIds.has(edgeId)) return;
                const edge = edges.get(edgeId);
                if (!edge) return;
                const update = { id: edge.id };
                if (edge.originalColor) update.color = edge.originalColor;
                if (typeof edge.originalWidth === 'number') update.width = edge.originalWidth;
                if (edge.originalDashes !== undefined) update.dashes = edge.originalDashes;
                if (edge.originalShadow !== undefined) update.shadow = edge.originalShadow;
                edges.update(update);
            });

            currentEdgeIds.forEach((edgeId) => {
                const edge = edges.get(edgeId);
                if (!edge) return;
                edges.update({
                    id: edge.id,
                    color: { color: '#06b6d4', highlight: '#22d3ee', hover: '#67e8f9' },
                    width: Math.max((edge.originalWidth || edge.width || 2) + 5.5, 9),
                    dashes: [12, 4],
                    shadow: {
                        enabled: true,
                        color: 'rgba(103, 232, 249, 0.9)',
                        size: 18,
                        x: 0,
                        y: 0
                    }
                });
            });

            if (network) {
                if (currentNodeIds.size || currentEdgeIds.size) {
                    network.selectNodes(Array.from(currentNodeIds), false);
                    network.selectEdges(Array.from(currentEdgeIds));
                } else if (lastHighlightedNodeIds.size || lastHighlightedEdgeIds.size) {
                    network.unselectAll();
                }
            }

            lastHighlightedNodeIds = currentNodeIds;
            lastHighlightedEdgeIds = currentEdgeIds;
        }

        function restoreEdgeVisual(edgeId) {
            if (!edges || !edgeId) return;
            const edge = edges.get(edgeId);
            if (!edge) return;
            const update = { id: edge.id };
            if (edge.originalColor) update.color = edge.originalColor;
            if (typeof edge.originalWidth === 'number') update.width = edge.originalWidth;
            if (edge.originalDashes !== undefined) update.dashes = edge.originalDashes;
            edges.update(update);
        }

        function setHoveredEdge(edgeId) {
            if (!edges || !edgeId) return;
            hoveredEdgeId = edgeId;
        }

        function clearHoveredEdge(edgeId) {
            if (!hoveredEdgeId) return;
            if (edgeId && String(edgeId) !== String(hoveredEdgeId)) return;
            hoveredEdgeId = null;
        }

        function selectRouteSessionById(sessionId) {
            hasAutoFitInitialTopology = true;
            selectedRouteSessionId = sessionId;
            const active = getActiveRouteSession();
            selectedRouteSessionSignature = active ? getRouteSessionSignature(active) : null;
            updateRouteSessionsPanel();
            applyRouteSessionHighlight();
        }

        function clearRouteSessionSelection() {
            selectedRouteSessionId = null;
            selectedRouteSessionSignature = null;
            updateRouteSessionsPanel();
            applyRouteSessionHighlight();
        }

        function fitTopologyView(duration) {
            if (!network) return;
            network.fit({
                animation: {
                    duration: duration || 450,
                    easingFunction: 'easeInOutQuad'
                }
            });
        }

        function loadCompactPreferences() {
            // 普通模式暂时停用：忽略历史偏好，固定为精简模式。
            compactModeEnabled = true;
            try {
                const posRaw = localStorage.getItem(compactPositionStorageKey);
                const parsed = posRaw ? JSON.parse(posRaw) : {};
                switchManualPositions = (parsed && typeof parsed === 'object') ? parsed : {};
            } catch (err) {
                switchManualPositions = {};
            }
            const toggle = document.getElementById('compact-mode-toggle');
            if (toggle) {
                toggle.checked = true;
                toggle.disabled = true;
            }
        }

        function persistCompactPreferences() {
            try {
                localStorage.setItem(compactModeStorageKey, compactModeEnabled ? '1' : '0');
            } catch (err) {}
            try {
                localStorage.setItem(compactPositionStorageKey, JSON.stringify(switchManualPositions || {}));
            } catch (err) {}
        }

        function toggleCompactMode() {
            // 普通模式暂时停用：保持精简模式，不执行切换。
            compactModeEnabled = true;
        }

        function resolveSwitchDomainMap(graphNodes, graphEdges) {
            const nodeMap = new Map();
            graphNodes.forEach((nodeObj) => {
                const nodeId = nodeObj.id || nodeObj;
                nodeMap.set(String(nodeId), nodeObj.data || {});
            });

            const switchDomainMap = {};

            // 优先使用节点自身携带的域信息
            graphNodes.forEach((nodeObj) => {
                const nodeId = nodeObj.id || nodeObj;
                const nodeData = nodeObj.data || {};
                const nodeType = nodeData.node_type || 'unknown';
                if (nodeType !== 'switch') return;
                const domainRaw = nodeData.domain || nodeData.domain_id || nodeData.controller_id || nodeData.controller;
                if (domainRaw !== undefined && domainRaw !== null && domainRaw !== '') {
                    switchDomainMap[normalizeSwitchId(nodeId)] = String(domainRaw);
                }
            });

            // 回退：由 controller_switch 边推断交换机属于哪个控制器域
            graphEdges.forEach((edgeObj) => {
                const source = edgeObj.source;
                const target = edgeObj.target;
                const edgeData = edgeObj.data || {};
                if ((edgeData.edge_type || '') !== 'controller_switch') return;
                const sMeta = nodeMap.get(String(source)) || {};
                const tMeta = nodeMap.get(String(target)) || {};
                if (sMeta.node_type === 'controller' && tMeta.node_type === 'switch') {
                    const sid = normalizeSwitchId(target);
                    if (!switchDomainMap[sid]) switchDomainMap[sid] = String(source);
                } else if (tMeta.node_type === 'controller' && sMeta.node_type === 'switch') {
                    const sid = normalizeSwitchId(source);
                    if (!switchDomainMap[sid]) switchDomainMap[sid] = String(target);
                }
            });

            // 再回退：按边携带 controller 字段推断
            graphEdges.forEach((edgeObj) => {
                const source = edgeObj.source;
                const target = edgeObj.target;
                const edgeData = edgeObj.data || {};
                if ((edgeData.edge_type || '') !== 'switch_link') return;
                const controller = edgeData.controller;
                if (controller === undefined || controller === null || controller === '') return;
                const sMeta = nodeMap.get(String(source)) || {};
                const tMeta = nodeMap.get(String(target)) || {};
                if (sMeta.node_type === 'switch') {
                    const sid = normalizeSwitchId(source);
                    if (!switchDomainMap[sid]) switchDomainMap[sid] = String(controller);
                }
                if (tMeta.node_type === 'switch') {
                    const sid = normalizeSwitchId(target);
                    if (!switchDomainMap[sid]) switchDomainMap[sid] = String(controller);
                }
            });

            return switchDomainMap;
        }

        function buildCompactGraphData(graphNodes, graphEdges) {
            const switchDomainMap = resolveSwitchDomainMap(graphNodes, graphEdges);
            const compactNodes = [];
            const seenSwitch = new Set();
            graphNodes.forEach((nodeObj) => {
                const nodeId = nodeObj.id || nodeObj;
                const nodeData = nodeObj.data || {};
                if ((nodeData.node_type || 'unknown') !== 'switch') return;
                const sid = normalizeSwitchId(nodeId);
                if (seenSwitch.has(sid)) return;
                compactNodes.push(nodeObj);
                seenSwitch.add(sid);
                if (!switchDomainMap[sid]) {
                    switchDomainMap[sid] = 'Domain-Unknown';
                }
            });

            const compactEdgeMap = new Map();
            graphEdges.forEach((edgeObj) => {
                const source = edgeObj.source;
                const target = edgeObj.target;
                const edgeData = edgeObj.data || {};
                const edgeType = edgeData.edge_type || '';
                if (edgeType !== 'switch_link') return;
                const s = normalizeSwitchId(source);
                const t = normalizeSwitchId(target);
                if (!seenSwitch.has(s) || !seenSwitch.has(t)) return;
                const key = canonicalSwitchLinkKey(s, t);
                const existing = compactEdgeMap.get(key);
                if (!existing) {
                    compactEdgeMap.set(key, {
                        source: source,
                        target: target,
                        data: Object.assign({ edge_type: 'switch_link' }, edgeData || {})
                    });
                    return;
                }

                // 去重时合并双向链路指标，优先保留有值且更“保守/可读”的结果
                const merged = existing.data || {};
                const incoming = edgeData || {};
                const pickNumeric = (a, b, prefer) => {
                    const na = Number(a), nb = Number(b);
                    const va = Number.isFinite(na), vb = Number.isFinite(nb);
                    if (!va && !vb) return (a !== undefined ? a : b);
                    if (!va) return nb;
                    if (!vb) return na;
                    if (prefer === 'min') return Math.min(na, nb);
                    if (prefer === 'max') return Math.max(na, nb);
                    return (na + nb) / 2;
                };

                if (incoming.delay !== undefined || merged.delay !== undefined) {
                    merged.delay = pickNumeric(merged.delay, incoming.delay, 'avg');
                }
                if (incoming.bw !== undefined || merged.bw !== undefined) {
                    merged.bw = pickNumeric(merged.bw, incoming.bw, 'min');
                }
                if (incoming.loss !== undefined || merged.loss !== undefined) {
                    merged.loss = pickNumeric(merged.loss, incoming.loss, 'max');
                }
                if (incoming.src_port !== undefined && merged.src_port === undefined) merged.src_port = incoming.src_port;
                if (incoming.dst_port !== undefined && merged.dst_port === undefined) merged.dst_port = incoming.dst_port;
                if (incoming.controller !== undefined && merged.controller === undefined) merged.controller = incoming.controller;
                existing.data = merged;
            });

            const compactEdges = Array.from(compactEdgeMap.values());
            return { nodes: compactNodes, edges: compactEdges, switchDomainMap: switchDomainMap };
        }

        function buildDomainRegionMeta(switchDomainMap, domainCenterHints) {
            const switchIds = nodes.getIds();
            const domains = new Map();
            switchIds.forEach((sid) => {
                const domainName = switchDomainMap[String(sid)] || 'Domain-Unknown';
                if (!domains.has(domainName)) domains.set(domainName, []);
                domains.get(domainName).push(sid);
            });

            const regions = [];
            let colorIndex = 0;
            domains.forEach((sidList, domainName) => {
                const positions = network.getPositions(sidList);
                const vals = sidList.map(sid => positions[sid]).filter(Boolean);
                if (!vals.length) return;

                let cx = vals.reduce((acc, p) => acc + p.x, 0) / vals.length;
                let cy = vals.reduce((acc, p) => acc + p.y, 0) / vals.length;
                if (domainCenterHints && domainCenterHints[domainName]) {
                    cx = domainCenterHints[domainName].x;
                    cy = domainCenterHints[domainName].y;
                }

                let maxDist = 120;
                vals.forEach((p) => {
                    const d = Math.hypot(p.x - cx, p.y - cy);
                    if (d > maxDist) maxDist = d;
                });
                const hintRadius = domainCenterHints && domainCenterHints[domainName]
                    ? (domainCenterHints[domainName].radius || 0)
                    : 0;
                const regionRadius = Math.max(maxDist + 100, hintRadius + 40);

                regions.push({
                    domainName: domainName,
                    cx: cx,
                    cy: cy,
                    radius: regionRadius,
                    fillColor: domainRegionColors[colorIndex % domainRegionColors.length],
                    strokeColor: 'rgba(251, 191, 36, 0.72)'
                });
                colorIndex += 1;
            });
            domainRegions = regions;
        }

        function drawDomainRegions(ctx) {
            if (!compactModeEnabled || !domainRegions.length) return;
            ctx.save();
            ctx.textAlign = 'center';
            ctx.textBaseline = 'middle';
            ctx.font = '700 15px Arial';
            domainRegions.forEach((region) => {
                // 区域边界更显眼：双层圆环 + 轻微发光
                ctx.beginPath();
                ctx.arc(region.cx, region.cy, region.radius, 0, Math.PI * 2);
                ctx.fillStyle = region.fillColor;
                ctx.shadowColor = 'rgba(245, 158, 11, 0.24)';
                ctx.shadowBlur = 20;
                ctx.fill();

                ctx.shadowBlur = 0;
                ctx.lineWidth = 3.4;
                ctx.strokeStyle = region.strokeColor;
                ctx.stroke();

                ctx.beginPath();
                ctx.arc(region.cx, region.cy, region.radius + 12, 0, Math.PI * 2);
                ctx.setLineDash([8, 6]);
                ctx.lineWidth = 1.2;
                ctx.strokeStyle = 'rgba(148, 163, 184, 0.55)';
                ctx.stroke();
                ctx.setLineDash([]);

                ctx.fillStyle = '#f8fafc';
                ctx.fillText(region.domainName, region.cx, region.cy - region.radius - 22);
            });
            ctx.restore();
        }

        function buildCompactAdjacency(compactEdges, switchDomainMap) {
            const switchAdj = new Map();
            const domainAdj = new Map();

            compactEdges.forEach((edge) => {
                const a = String(edge.source);
                const b = String(edge.target);
                if (!switchAdj.has(a)) switchAdj.set(a, new Set());
                if (!switchAdj.has(b)) switchAdj.set(b, new Set());
                switchAdj.get(a).add(b);
                switchAdj.get(b).add(a);

                const da = switchDomainMap[a] || 'Domain-Unknown';
                const db = switchDomainMap[b] || 'Domain-Unknown';
                if (!domainAdj.has(da)) domainAdj.set(da, new Map());
                if (!domainAdj.has(db)) domainAdj.set(db, new Map());
                if (da !== db) {
                    domainAdj.get(da).set(db, (domainAdj.get(da).get(db) || 0) + 1);
                    domainAdj.get(db).set(da, (domainAdj.get(db).get(da) || 0) + 1);
                }
            });

            return { switchAdj: switchAdj, domainAdj: domainAdj };
        }

        function chooseDomainCenter(domainNames, domainAdj) {
            let best = domainNames[0] || 'Domain-Unknown';
            let bestScore = -1;
            domainNames.forEach((d) => {
                const neigh = domainAdj.get(d) || new Map();
                let total = 0;
                neigh.forEach(v => { total += v; });
                const score = neigh.size * 1000 + total;
                if (score > bestScore) {
                    bestScore = score;
                    best = d;
                }
            });
            return best;
        }

        function bfsHopMap(centerSwitchKey, memberKeys, switchAdj) {
            const allowed = new Set(memberKeys);
            const hops = {};
            memberKeys.forEach(k => { hops[k] = Number.POSITIVE_INFINITY; });
            hops[centerSwitchKey] = 0;
            const queue = [centerSwitchKey];
            while (queue.length) {
                const cur = queue.shift();
                const nextHop = hops[cur] + 1;
                const neigh = switchAdj.get(cur) || new Set();
                neigh.forEach((n) => {
                    if (!allowed.has(n)) return;
                    if (nextHop < hops[n]) {
                        hops[n] = nextHop;
                        queue.push(n);
                    }
                });
            }
            let maxFinite = 0;
            memberKeys.forEach((k) => {
                if (Number.isFinite(hops[k])) maxFinite = Math.max(maxFinite, hops[k]);
            });
            memberKeys.forEach((k) => {
                if (!Number.isFinite(hops[k])) hops[k] = maxFinite + 1;
            });
            return hops;
        }

        function normalizeAngle(a) {
            let v = a;
            while (v <= -Math.PI) v += Math.PI * 2;
            while (v > Math.PI) v -= Math.PI * 2;
            return v;
        }

        function angleDistance(a, b) {
            return Math.abs(normalizeAngle(a - b));
        }

        function buildRingAnglesWithOptimization(items, preferredAngles, basePhase) {
            const n = items.length;
            const result = {};
            if (!n) return result;
            if (n === 1) {
                const only = items[0];
                result[only] = preferredAngles.has(only) ? preferredAngles.get(only) : (basePhase || 0);
                return result;
            }

            const sortedItems = items.slice().sort((a, b) => {
                const aa = preferredAngles.has(a) ? preferredAngles.get(a) : 0;
                const bb = preferredAngles.has(b) ? preferredAngles.get(b) : 0;
                return aa - bb;
            });

            const step = (2 * Math.PI) / n;
            const slots = [];
            for (let i = 0; i < n; i++) {
                slots.push((basePhase || 0) + i * step);
            }

            let bestCost = Number.POSITIVE_INFINITY;
            let bestShift = 0;
            for (let shift = 0; shift < n; shift++) {
                let cost = 0;
                for (let i = 0; i < n; i++) {
                    const key = sortedItems[i];
                    const pref = preferredAngles.has(key) ? preferredAngles.get(key) : slots[(i + shift) % n];
                    const slotAngle = slots[(i + shift) % n];
                    cost += angleDistance(pref, slotAngle);
                }
                if (cost < bestCost) {
                    bestCost = cost;
                    bestShift = shift;
                }
            }

            for (let i = 0; i < n; i++) {
                result[sortedItems[i]] = slots[(i + bestShift) % n];
            }
            return result;
        }

        function applyCompactLayout(graphNodes, switchDomainMap, compactEdges) {
            const switchNodes = graphNodes
                .map(item => {
                    const rawId = item.id || item;
                    return {
                        id: rawId,
                        key: normalizeSwitchId(rawId),
                        data: item.data || {}
                    };
                })
                .filter(item => (item.data.node_type || 'unknown') === 'switch');

            const domainMap = new Map();
            switchNodes.forEach((item) => {
                const domainName = switchDomainMap[item.key] || 'Domain-Unknown';
                if (!domainMap.has(domainName)) domainMap.set(domainName, []);
                domainMap.get(domainName).push(item);
            });

            const domainNames = Array.from(domainMap.keys()).sort();
            const { switchAdj, domainAdj } = buildCompactAdjacency(compactEdges || [], switchDomainMap);

            // 预估各区域半径（用于区域级防重叠布局）
            const estimatedDomainRadius = {};
            domainNames.forEach((d) => {
                const count = (domainMap.get(d) || []).length;
                estimatedDomainRadius[d] = Math.max(320, 250 + Math.sqrt(Math.max(count, 1)) * 70);
            });

            // ===== 区域级：同心圆 + 圆心（带防重叠）=====
            const domainCenterName = chooseDomainCenter(domainNames, domainAdj);
            const domainPos = {};
            const centerSpacing = 0;
            domainPos[domainCenterName] = { x: centerSpacing, y: centerSpacing };
            let prevOuterBoundary = estimatedDomainRadius[domainCenterName] || 360;

            const remainDomains = domainNames.filter(n => n !== domainCenterName);
            let cursor = 0;
            let ring = 1;
            while (cursor < remainDomains.length) {
                const capacity = Math.max(6 * ring, 6);
                const ringNodes = remainDomains.slice(cursor, cursor + capacity);
                if (!ringNodes.length) break;

                // 半径下界1：与上一层（或中心）的径向间隔足够
                const maxRingNodeRadius = Math.max(...ringNodes.map(d => estimatedDomainRadius[d] || 360));
                let ringRadius = prevOuterBoundary + maxRingNodeRadius + 260;

                // 半径下界2：同一环上相邻区域弧长足够，避免互相重叠
                if (ringNodes.length > 1) {
                    const theta = Math.PI / ringNodes.length;
                    const denom = 2 * Math.sin(theta);
                    if (denom > 0.0001) {
                        let minByArc = 0;
                        for (let i = 0; i < ringNodes.length; i++) {
                            const a = ringNodes[i];
                            const b = ringNodes[(i + 1) % ringNodes.length];
                            const requiredCenterDistance =
                                (estimatedDomainRadius[a] || 360) +
                                (estimatedDomainRadius[b] || 360) + 220;
                            minByArc = Math.max(minByArc, requiredCenterDistance / denom);
                        }
                        ringRadius = Math.max(ringRadius, minByArc);
                    }
                }

                // 根据相邻区域的已知位置，优化该环上的角度分配，尽量缩短区域间连线
                const preferredAngles = new Map();
                ringNodes.forEach((d) => {
                    const neighbors = domainAdj.get(d) || new Map();
                    let vx = 0;
                    let vy = 0;
                    let totalW = 0;
                    neighbors.forEach((w, nd) => {
                        if (!domainPos[nd]) return;
                        vx += domainPos[nd].x * w;
                        vy += domainPos[nd].y * w;
                        totalW += w;
                    });
                    if (totalW > 0) {
                        preferredAngles.set(d, Math.atan2(vy, vx));
                    } else {
                        preferredAngles.set(d, 0);
                    }
                });
                const anglePlan = buildRingAnglesWithOptimization(
                    ringNodes,
                    preferredAngles,
                    (ring % 2 ? 0.18 : 0)
                );
                ringNodes.forEach((d) => {
                    const angle = anglePlan[d];
                    domainPos[d] = {
                        x: ringRadius * Math.cos(angle),
                        y: ringRadius * Math.sin(angle)
                    };
                });
                prevOuterBoundary = ringRadius + maxRingNodeRadius;
                cursor += ringNodes.length;
                ring += 1;
            }

            // ===== 区域内：按“中心交换机 + 跳数同心圆”布局 =====
            const regionHints = {};
            let manualPosDirty = false;
            domainNames.forEach((domainName, domainIndex) => {
                const members = domainMap.get(domainName) || [];
                if (!members.length) return;
                const memberKeys = members.map(m => m.key);
                const memberSet = new Set(memberKeys);

                // 连接最多的交换机作为圆心（域内邻接优先）
                let centerSwitchKey = memberKeys[0];
                let centerScore = -1;
                memberKeys.forEach((k) => {
                    const neigh = switchAdj.get(k) || new Set();
                    let intra = 0;
                    let total = 0;
                    neigh.forEach((n) => {
                        total += 1;
                        if ((switchDomainMap[n] || 'Domain-Unknown') === domainName) intra += 1;
                    });
                    const score = intra * 1000 + total;
                    if (score > centerScore) {
                        centerScore = score;
                        centerSwitchKey = k;
                    }
                });

                const hops = bfsHopMap(centerSwitchKey, memberKeys, switchAdj);
                const rings = new Map();
                memberKeys.forEach((k) => {
                    const h = hops[k];
                    if (!rings.has(h)) rings.set(h, []);
                    rings.get(h).push(k);
                });

                const center = domainPos[domainName] || { x: 0, y: 0 };
                const manualAnchorLimit = (estimatedDomainRadius[domainName] || 320) * 1.45;
                const resolveManualPos = (manualPos) => {
                    if (!manualPos || !Number.isFinite(manualPos.x) || !Number.isFinite(manualPos.y)) return null;
                    const d = Math.hypot(manualPos.x - center.x, manualPos.y - center.y);
                    return d <= manualAnchorLimit ? manualPos : null;
                };
                // 动态环间距：域内节点/连线越多，间距越大，减少拥挤
                let intraEdgeCount = 0;
                memberKeys.forEach((k) => {
                    const neigh = switchAdj.get(k) || new Set();
                    neigh.forEach((n) => {
                        if (memberSet.has(n) && k < n) intraEdgeCount += 1;
                    });
                });
                const n = memberKeys.length;
                const maxIntraEdges = Math.max(1, (n * (n - 1)) / 2);
                const intraDensity = Math.min(1, intraEdgeCount / maxIntraEdges);
                const avgIntraDegree = n > 0 ? (2 * intraEdgeCount) / n : 0;

                const ringGapBase = 120;
                const ringGapByNodeCount = Math.sqrt(Math.max(n, 1)) * 16;
                const ringGapByDensity = intraDensity * 70;
                const ringGapByDegree = avgIntraDegree * 10;
                const ringGap = Math.min(
                    340,
                    Math.max(
                        135,
                        ringGapBase + ringGapByNodeCount + ringGapByDensity + ringGapByDegree
                    )
                );
                let maxHop = 0;

                // 圆心节点
                const centerMember = members.find(m => m.key === centerSwitchKey);
                if (centerMember) {
                    const manualCenter = resolveManualPos(switchManualPositions[centerMember.key]);
                    if (!manualCenter && switchManualPositions[centerMember.key]) {
                        delete switchManualPositions[centerMember.key];
                        manualPosDirty = true;
                    }
                    nodes.update({
                        id: centerMember.id,
                        x: (manualCenter && Number.isFinite(manualCenter.x)) ? manualCenter.x : center.x,
                        y: (manualCenter && Number.isFinite(manualCenter.y)) ? manualCenter.y : center.y,
                        fixed: false
                    });
                }

                // 同心环节点（按跳数）
                const sortedHops = Array.from(rings.keys()).filter(h => h > 0).sort((a, b) => a - b);
                const localPlacedPos = {};
                if (centerMember) {
                    const pp = nodes.get(centerMember.id);
                    if (pp && Number.isFinite(pp.x) && Number.isFinite(pp.y)) {
                        localPlacedPos[centerMember.key] = { x: pp.x, y: pp.y };
                    } else {
                        localPlacedPos[centerMember.key] = { x: center.x, y: center.y };
                    }
                }
                sortedHops.forEach((h) => {
                    maxHop = Math.max(maxHop, h);
                    const ringMembers = rings.get(h) || [];
                    // 同一跳数层节点越多，该圈层再额外外扩，避免同圈拥挤
                    const occupancyBoost = Math.sqrt(Math.max(ringMembers.length, 1)) * 18;
                    const rr = ringGap * h + occupancyBoost;
                    const preferredAngles = new Map();
                    ringMembers.forEach((k) => {
                        const neigh = switchAdj.get(k) || new Set();
                        let vx = 0;
                        let vy = 0;
                        let count = 0;
                        neigh.forEach((n) => {
                            // 优先对齐已放置的本域邻居，减少域内连线长度
                            if (localPlacedPos[n]) {
                                vx += localPlacedPos[n].x - center.x;
                                vy += localPlacedPos[n].y - center.y;
                                count += 2;
                                return;
                            }
                            // 跨域邻居引导角度，减少域间连线长度
                            const nd = switchDomainMap[n] || 'Domain-Unknown';
                            if (nd !== domainName && domainPos[nd]) {
                                vx += domainPos[nd].x - center.x;
                                vy += domainPos[nd].y - center.y;
                                count += 1;
                            }
                        });
                        if (count > 0 && (vx !== 0 || vy !== 0)) {
                            preferredAngles.set(k, Math.atan2(vy, vx));
                        } else {
                            preferredAngles.set(k, domainIndex * 0.23 + h * 0.17);
                        }
                    });
                    const anglePlan = buildRingAnglesWithOptimization(
                        ringMembers,
                        preferredAngles,
                        domainIndex * 0.23 + h * 0.17
                    );
                    ringMembers.forEach((k) => {
                        const m = members.find(x => x.key === k);
                        if (!m) return;
                        const manualPos = resolveManualPos(switchManualPositions[m.key]);
                        if (!manualPos && switchManualPositions[m.key]) {
                            delete switchManualPositions[m.key];
                            manualPosDirty = true;
                        }
                        let x = center.x;
                        let y = center.y;
                        if (manualPos && Number.isFinite(manualPos.x) && Number.isFinite(manualPos.y)) {
                            x = manualPos.x;
                            y = manualPos.y;
                        } else {
                            const angle = anglePlan[k];
                            x = center.x + rr * Math.cos(angle);
                            y = center.y + rr * Math.sin(angle);
                        }
                        localPlacedPos[m.key] = { x: x, y: y };
                        nodes.update({
                            id: m.id,
                            x: x,
                            y: y,
                            fixed: false
                        });
                    });
                });

                const baseRadius = Math.max(
                    estimatedDomainRadius[domainName] || 260,
                    ringGap * Math.max(1, maxHop + 0.95) + Math.sqrt(members.length) * 30 + intraDensity * 50
                );
                regionHints[domainName] = {
                    x: center.x,
                    y: center.y,
                    radius: baseRadius
                };
            });

            // 二次防重叠：按区域圆半径做碰撞分离，并整体平移区域内交换机
            const domainShift = {};
            domainNames.forEach((d) => { domainShift[d] = { x: 0, y: 0 }; });
            const minGap = 130;
            const relaxIter = 26;
            for (let it = 0; it < relaxIter; it++) {
                let moved = false;
                for (let i = 0; i < domainNames.length; i++) {
                    for (let j = i + 1; j < domainNames.length; j++) {
                        const da = domainNames[i];
                        const db = domainNames[j];
                        const a = regionHints[da];
                        const b = regionHints[db];
                        if (!a || !b) continue;
                        const dx = b.x - a.x;
                        const dy = b.y - a.y;
                        const dist = Math.hypot(dx, dy) || 0.0001;
                        const required = (a.radius || 0) + (b.radius || 0) + minGap;
                        if (dist >= required) continue;
                        const overlap = required - dist;
                        const ux = dx / dist;
                        const uy = dy / dist;
                        const push = overlap * 0.53;
                        a.x -= ux * push;
                        a.y -= uy * push;
                        b.x += ux * push;
                        b.y += uy * push;
                        domainShift[da].x -= ux * push;
                        domainShift[da].y -= uy * push;
                        domainShift[db].x += ux * push;
                        domainShift[db].y += uy * push;
                        moved = true;
                    }
                }
                if (!moved) break;
            }

            // 将每个域的位移应用到域内交换机，保持域内相对结构不变
            domainNames.forEach((domainName) => {
                const delta = domainShift[domainName] || { x: 0, y: 0 };
                if ((Math.abs(delta.x) + Math.abs(delta.y)) < 0.001) return;
                const members = domainMap.get(domainName) || [];
                members.forEach((m) => {
                    const node = nodes.get(m.id);
                    if (!node) return;
                    nodes.update({
                        id: m.id,
                        x: (node.x || 0) + delta.x,
                        y: (node.y || 0) + delta.y,
                        fixed: false
                    });
                });
            });

            if (manualPosDirty) {
                persistCompactPreferences();
            }

            buildDomainRegionMeta(switchDomainMap, regionHints);
        }

        function cacheDraggedSwitchPositions(nodeIds) {
            if (!compactModeEnabled || !nodeIds || !nodeIds.length) return;
            const positions = network.getPositions(nodeIds);
            nodeIds.forEach((nodeId) => {
                const node = nodes.get(nodeId);
                if (!node || node.nodeType !== 'switch') return;
                const p = positions[nodeId];
                if (!p) return;
                switchManualPositions[String(nodeId)] = { x: p.x, y: p.y };
            });
            persistCompactPreferences();
            buildDomainRegionMeta(currentSwitchDomainMap || {});
        }

        function stopAllLinkRemovalBlinks() {
            for (const id in linkRemovalBlinkTimers) {
                const s = linkRemovalBlinkTimers[id];
                clearInterval(s.intervalId);
                clearTimeout(s.timeoutId);
            }
            linkRemovalBlinkTimers = {};
        }

        function extractPrevSwitchLinkEndpoints(edgeDataSet) {
            const map = new Map();
            edgeDataSet.get().forEach(function(e) {
                const et = (e.data && e.data.edge_type) || '';
                if (et === 'switch_link' && !(e.data && e.data.phantom_removal)) {
                    map.set(canonicalSwitchLinkKey(e.from, e.to), { from: e.from, to: e.to });
                }
            });
            return map;
        }

        function startLinkRemovalBlink(edgeId) {
            let on = true;
            function tick() {
                on = !on;
                try {
                    edges.update({
                        id: edgeId,
                        color: on
                            ? { color: '#ef4444', highlight: '#f87171', hover: '#fca5a5' }
                            : { color: '#f97316', highlight: '#fb923c', hover: '#fdba74' },
                        width: on ? 5 : 3
                    });
                } catch (err) {}
            }
            tick();
            const intervalId = setInterval(tick, 250);
            const timeoutId = setTimeout(function() {
                clearInterval(intervalId);
                delete linkRemovalBlinkTimers[edgeId];
                try { edges.remove(edgeId); } catch (e2) {}
            }, 3000);
            linkRemovalBlinkTimers[edgeId] = { intervalId: intervalId, timeoutId: timeoutId };
        }

        // 创建SVG图标（基于lucide-react图标，与SDN.txt保持一致）
        function createIconSVG(iconType, color) {
            const svgMap = {
                'globe': '<svg xmlns="http://www.w3.org/2000/svg" viewBox="0 0 24 24" fill="none" stroke="' + color + '" stroke-width="2" stroke-linecap="round" stroke-linejoin="round"><circle cx="12" cy="12" r="10"/><line x1="2" y1="12" x2="22" y2="12"/><path d="M12 2a15.3 15.3 0 0 1 4 10 15.3 15.3 0 0 1-4 10 15.3 15.3 0 0 1-4-10 15.3 15.3 0 0 1 4-10z"/></svg>',
                'server': '<svg xmlns="http://www.w3.org/2000/svg" viewBox="0 0 24 24" fill="none" stroke="' + color + '" stroke-width="2" stroke-linecap="round" stroke-linejoin="round"><rect x="2" y="2" width="20" height="8" rx="2" ry="2"/><rect x="2" y="14" width="20" height="8" rx="2" ry="2"/><line x1="6" y1="6" x2="6.01" y2="6"/><line x1="6" y1="18" x2="6.01" y2="18"/></svg>',
                'network': '<svg xmlns="http://www.w3.org/2000/svg" viewBox="0 0 24 24" fill="none" stroke="' + color + '" stroke-width="2" stroke-linecap="round" stroke-linejoin="round"><rect x="16" y="16" width="6" height="6" rx="1"/><rect x="2" y="16" width="6" height="6" rx="1"/><rect x="9" y="2" width="6" height="6" rx="1"/><path d="M5 16v-6a1 1 0 0 1 1-1h12a1 1 0 0 1 1 1v6"/><path d="M12 12V8"/></svg>',
                'laptop': '<svg xmlns="http://www.w3.org/2000/svg" viewBox="0 0 24 24" fill="none" stroke="' + color + '" stroke-width="2" stroke-linecap="round" stroke-linejoin="round"><rect x="2" y="4" width="20" height="12" rx="2" ry="2"/><line x1="2" y1="16" x2="22" y2="16"/><line x1="6" y1="20" x2="6.01" y2="20"/><line x1="10" y1="20" x2="10.01" y2="20"/><line x1="14" y1="20" x2="14.01" y2="20"/><line x1="18" y1="20" x2="18.01" y2="20"/></svg>'
            };
            return svgMap[iconType] || svgMap['laptop'];
        }

        // 将SVG转换为data URI
        function svgToDataURI(svgString) {
            const encoded = encodeURIComponent(svgString);
            return 'data:image/svg+xml;charset=utf-8,' + encoded;
        }

        // 初始化网络图
        function initNetwork() {
            try {
                console.log('开始初始化网络图...');

                // 检查vis库是否加载
                if (typeof vis === 'undefined') {
                    console.error('vis.js库未加载！');
                    document.getElementById('network').innerHTML = '<div style="padding: 50px; text-align: center; color: red;"><h2>错误：vis.js库加载失败</h2><p>请检查网络连接或使用离线版本</p></div>';
                    return;
                }

                console.log('vis.js库已加载');

                const container = document.getElementById('network');
                nodes = new vis.DataSet([]);
                edges = new vis.DataSet([]);

                console.log('DataSet创建完成');

                const data = { nodes: nodes, edges: edges };
                const options = {
                nodes: {
                    font: {
                        size: 12,
                        color: '#e2e8f0',
                        face: 'Arial',
                        bold: true
                    },
                    borderWidth: 2,
                    shadow: {
                        enabled: true,
                        color: 'rgba(0,0,0,0.5)',
                        size: 10,
                        x: 2,
                        y: 2
                    },
                    chosen: false,
                    shapeProperties: {
                        useBorderWithImage: true
                    }
                },
                edges: {
                    width: 2,
                    color: {
                        color: '#475569',
                        highlight: '#60a5fa',
                        hover: '#60a5fa'
                    },
                    shadow: {
                        enabled: true,
                        color: 'rgba(0,0,0,0.3)',
                        size: 5
                    },
                    smooth: {
                        enabled: true,
                        type: 'curvedCW',
                        roundness: 0.2
                    },
                    chosen: false,
                    hoverWidth: 0,
                    selectionWidth: 0,
                    arrows: {
                        to: {
                            enabled: true,
                            scaleFactor: 0.6,
                            type: 'arrow'
                        }
                    }
                },
                layout: {
                    hierarchical: {
                        enabled: false
                    }
                },
                physics: {
                    enabled: false
                },
                interaction: {
                    hover: true,
                    tooltipDelay: 100,
                    dragNodes: true,
                    dragView: true,
                    zoomView: true,
                    selectConnectedEdges: false
                },
                configure: {
                    enabled: false
                }
            };

                console.log('开始创建vis.Network...');
                network = new vis.Network(container, data, options);
                console.log('vis.Network创建完成');
                loadCompactPreferences();
                updateRouteSessionsPanel();

                network.on('afterDrawing', function(ctx) {
                    drawDomainRegions(ctx);
                });

                // 节点点击事件
                network.on('click', function(params) {
                    if (params.nodes.length > 0) {
                        showNodeInfo(params.nodes[0]);
                        // 确保侧边栏显示
                        document.getElementById('sidebar').style.display = 'flex';
                    } else if (params.edges.length > 0) {
                        showEdgeInfo(params.edges[0]);
                        document.getElementById('sidebar').style.display = 'flex';
                    } else {
                        // 点击空白处不关闭侧边栏，保持选中状态
                    }
                });
                network.on('hoverEdge', function(params) {
                    if (params && params.edge) {
                        setHoveredEdge(params.edge);
                    }
                });
                network.on('blurEdge', function(params) {
                    clearHoveredEdge(params && params.edge);
                });
                const routeSessionsList = document.getElementById('route-sessions-list');
                if (routeSessionsList) {
                    routeSessionsList.addEventListener('click', function(event) {
                        const item = event.target.closest('.route-session-item');
                        if (!item) return;
                        const sessionId = item.getAttribute('data-session-id');
                        if (sessionId) {
                            selectRouteSessionById(sessionId);
                        }
                    });
                }
                network.on('dragEnd', function(params) {
                    if (params && Array.isArray(params.nodes) && params.nodes.length > 0) {
                        cacheDraggedSwitchPositions(params.nodes);
                    }
                });

                console.log('事件监听器已设置');

                // 加载拓扑
                console.log('准备加载拓扑数据...');
                refreshTopology();

                // 自动刷新（每5秒）
                setInterval(refreshTopology, 5000);
                setInterval(refreshSelectedSwitchFlows, 3000);
                console.log('自动刷新已启用（每5秒）');

            } catch (err) {
                console.error('初始化网络图失败:', err);
                document.getElementById('network').innerHTML = '<div style="padding: 50px; text-align: center; color: red;"><h2>初始化失败</h2><p>' + err.message + '</p></div>';
            }
        }

        // 刷新拓扑数据
        async function refreshTopology() {
            if (isRefreshInFlight) return;
            isRefreshInFlight = true;
            try {
                debugLog('正在获取拓扑数据...');
                const response = await fetch('/api/graph?include_flows=0');

                if (!response.ok) {
                    throw new Error(`HTTP错误: ${response.status} ${response.statusText}`);
                }

                const data = await response.json();
                debugLog('成功获取拓扑数据:', data);
                refreshGraphMetadataCache(data);

                try {
                    const routeResp = await fetch('/api/route_sessions');
                    if (routeResp.ok) {
                        const routeData = await routeResp.json();
                        routeSessions = Array.isArray(routeData.sessions) ? routeData.sessions : [];
                    } else {
                        routeSessions = [];
                    }
                } catch (routeErr) {
                    console.warn('获取 route_sessions 失败:', routeErr);
                    routeSessions = [];
                }
                if (selectedRouteSessionId && !routeSessions.some((item) => item.id === selectedRouteSessionId)) {
                    let reassignedId = null;
                    if (selectedRouteSessionSignature) {
                        const matched = routeSessions.find((item) => getRouteSessionSignature(item) === selectedRouteSessionSignature);
                        if (matched) {
                            reassignedId = matched.id;
                        }
                    }
                    selectedRouteSessionId = reassignedId;
                }
                if (selectedRouteSessionId) {
                    const active = routeSessions.find((item) => item.id === selectedRouteSessionId);
                    selectedRouteSessionSignature = active ? getRouteSessionSignature(active) : selectedRouteSessionSignature;
                } else if (!routeSessions.length) {
                    selectedRouteSessionSignature = null;
                }
                updateRouteSessionsPanel();

                const topologySignature = computeTopologySignature(data);
                if (topologySignature !== lastTopologySignature) {
                    updateNetwork(data);
                    lastTopologySignature = topologySignature;
                } else {
                    applyRouteSessionHighlight();
                }
                updateStatistics();
                const statusEl = document.getElementById('status');
                if (statusEl) {
                    statusEl.className = 'status connected';
                    statusEl.textContent = '● 已连接';
                }
            } catch (error) {
                console.error('获取拓扑数据失败:', error);
                console.error('错误详情:', error.message);
                routeSessions = [];
                selectedRouteSessionId = null;
                updateRouteSessionsPanel();
                const statusEl = document.getElementById('status');
                if (statusEl) {
                    statusEl.className = 'status error';
                    statusEl.textContent = '● 连接错误: ' + error.message;
                }
            } finally {
                isRefreshInFlight = false;
            }
        }

        // 更新网络图
        function updateNetwork(data) {
            try {
                const graphNodes = data.nodes || [];
                const graphEdges = data.edges || [];
                // 普通模式暂时停用：始终使用精简模式的数据构建。
                const renderData = buildCompactGraphData(graphNodes, graphEdges);
                const renderNodes = renderData.nodes || [];
                const renderEdges = renderData.edges || [];
                lastCompactLayoutData = {
                    nodes: renderNodes,
                    edges: renderEdges,
                    switchDomainMap: renderData.switchDomainMap || {}
                };

                debugLog('收到拓扑数据:', data);
                debugLog('节点数量:', renderNodes.length);
                debugLog('边数量:', renderEdges.length);

                stopAllLinkRemovalBlinks();
                const prevSwitchLinkMap = extractPrevSwitchLinkEndpoints(edges);
                const desiredNodes = [];
                const desiredEdges = [];
                const nextSwitchLinkEdgeIdsByKey = new Map();

                // 构建节点快照
                let addedNodes = 0;
                // 按节点类型分组，用于编号
                const nodeTypeCounters = {
                    'root_controller': 0,
                    'controller': 0,
                    'switch': 0,
                    'host': 0,
                    'unknown': 0
                };

                renderNodes.forEach((nodeObj, index) => {
                    try {
                        // 适配新的数据格式：{id: ..., data: {...}}
                        const nodeId = nodeObj.id || nodeObj;
                        const nodeData = nodeObj.data || {};
                        const nodeType = nodeData.node_type || 'unknown';

                        let color, size, iconType, label, iconColor;
                        let nodeNumber = getStableNodeNumber(nodeId);

                        // 根据节点类型设置样式和编号（使用SDN.txt风格的颜色和图标）
                        if (nodeId === 'RootController' || nodeType === 'root_controller') {
                            color = { background: '#92400e', border: '#f59e0b', highlight: { background: '#b45309', border: '#fbbf24' } };
                            size = 56;  // 对应w-14 h-14 (56px)
                            iconType = 'globe';
                            iconColor = '#f59e0b';
                            nodeTypeCounters['root_controller']++;
                            label = 'Root';
                        } else if (nodeType === 'controller') {
                            color = { background: '#1e3a8a', border: '#3b82f6', highlight: { background: '#1e40af', border: '#60a5fa' } };
                            size = 56;  // 对应w-14 h-14 (56px)
                            iconType = 'server';
                            iconColor = '#60a5fa';
                            nodeTypeCounters['controller']++;
                            label = 'Ctrl-' + nodeNumber;
                        } else if (nodeType === 'switch') {
                            color = { background: '#164e63', border: '#06b6d4', highlight: { background: '#155e75', border: '#22d3ee' } };
                            size = 36;
                            iconType = 'network';
                            iconColor = '#22d3ee';
                            nodeTypeCounters['switch']++;
                            label = formatSwitchLabel(nodeId);
                        } else if (nodeType === 'host') {
                            color = { background: '#1e293b', border: '#475569', highlight: { background: '#334155', border: '#64748b' } };
                            size = 32;  // 对应w-8 h-8 (32px)
                            iconType = 'laptop';
                            iconColor = '#94a3b8';
                            nodeTypeCounters['host']++;
                            label = formatHostLabel(nodeId, nodeData);
                        } else {
                            // 未知类型
                            color = { background: '#1e293b', border: '#64748b', highlight: { background: '#334155', border: '#94a3b8' } };
                            size = 32;
                            iconType = 'laptop';
                            iconColor = '#94a3b8';
                            nodeTypeCounters['unknown']++;
                            label = 'Unknown' + nodeNumber;
                        }

                        // 创建图标SVG并转换为data URI
                        const iconSVG = createIconSVG(iconType, iconColor);
                        const iconDataURI = svgToDataURI(iconSVG);

                        debugLog(`添加节点 ${index}: ID=${nodeId}, Type=${nodeType}, Label=${label}, Icon=${iconType}`);

                        // 存储完整的节点信息，包括原始数据和统计信息
                        desiredNodes.push({
                            id: nodeId,
                            label: label,
                            color: color,
                            size: size,
                            shape: 'image',  // 使用image形状
                            image: iconDataURI,  // 设置图标
                            brokenImage: iconDataURI,  // 备用图标
                            title: label,
                            nodeType: nodeType,
                            nodeNumber: nodeNumber,
                            nodeData: nodeData,  // 存储完整的节点数据
                            originalColor: color,
                            originalSize: size,
                            originalBorderWidth: 2,
                            originalShadow: {
                                enabled: true,
                                color: 'rgba(0,0,0,0.5)',
                                size: 10,
                                x: 2,
                                y: 2
                            }
                        });

                        addedNodes++;
                    } catch (err) {
                        console.error('添加节点失败:', nodeObj, err);
                    }
                });

                debugLog('已添加节点数:', addedNodes, '/', renderNodes.length);

                // 添加边
                let addedEdges = 0;
                const newSwitchLinkKeys = new Set();
                renderEdges.forEach((edgeObj) => {
                    try {
                        // 适配新的数据格式：{source: ..., target: ..., data: {...}}
                        let source, target, edgeData;

                        if (edgeObj.source !== undefined && edgeObj.target !== undefined) {
                            // 新格式
                            source = edgeObj.source;
                            target = edgeObj.target;
                            edgeData = edgeObj.data || {};
                        } else if (Array.isArray(edgeObj) && edgeObj.length >= 2) {
                            // 旧格式（兼容）
                            [source, target, edgeData] = edgeObj;
                        } else {
                            console.warn('无效的边格式:', edgeObj);
                            return;
                        }

                        const edgeType = (edgeData && edgeData.edge_type) || 'unknown';

                        let color, width, dashes, smooth;
                        let isInterDomain = false;
                        let sourceDomain = '';
                        let targetDomain = '';

                        if (edgeType === 'controller_connection') {
                            color = { color: '#d97706', highlight: '#f59e0b', hover: '#fbbf24' };
                            width = 3;
                            dashes = [10, 5];
                            smooth = false;  // 改为直线
                        } else if (edgeType === 'controller_switch') {
                            color = { color: '#3b82f6', highlight: '#60a5fa', hover: '#93c5fd' };
                            width = 2.5;
                            dashes = [5, 5];
                            smooth = false;  // 改为直线
                        } else if (edgeType === 'host_switch') {
                            color = { color: '#64748b', highlight: '#94a3b8', hover: '#cbd5e0' };
                            width = 1.5;
                            dashes = false;
                            smooth = { type: 'continuous' };
                        } else if (edgeType === 'switch_link') {
                            newSwitchLinkKeys.add(canonicalSwitchLinkKey(source, target));
                            sourceDomain = (renderData.switchDomainMap || {})[String(source)] || 'Domain-Unknown';
                            targetDomain = (renderData.switchDomainMap || {})[String(target)] || 'Domain-Unknown';
                            isInterDomain = sourceDomain !== targetDomain;
                            color = isInterDomain
                                ? { color: '#f59e0b', highlight: '#fbbf24', hover: '#fcd34d' }
                                : { color: '#22d3ee', highlight: '#67e8f9', hover: '#a5f3fc' };
                            width = isInterDomain ? 4.6 : 3.1;
                            dashes = false;
                            smooth = isInterDomain
                                ? { type: 'curvedCW', roundness: 0.28 }
                                : { type: 'curvedCW', roundness: 0.14 };
                        } else {
                            color = { color: '#475569', highlight: '#64748b', hover: '#94a3b8' };
                            width = 2;
                            dashes = false;
                            smooth = { type: 'curvedCW', roundness: 0.2 };
                        }

                        debugLog(`添加边 ${source} -> ${target} (${edgeType})`);

                        const safeEdgeData = Object.assign({}, edgeData || {});
                        safeEdgeData.edge_type = edgeType;
                        safeEdgeData.inter_domain = isInterDomain;
                        if (sourceDomain) safeEdgeData.source_domain = sourceDomain;
                        if (targetDomain) safeEdgeData.target_domain = targetDomain;

                        const edgeId = stableEdgeId(edgeType, source, target);
                        if (edgeType === 'switch_link') {
                            const linkKey = canonicalSwitchLinkKey(source, target);
                            if (!nextSwitchLinkEdgeIdsByKey.has(linkKey)) {
                                nextSwitchLinkEdgeIdsByKey.set(linkKey, []);
                            }
                            nextSwitchLinkEdgeIdsByKey.get(linkKey).push(edgeId);
                        }

                        desiredEdges.push({
                            id: edgeId,
                            from: source,
                            to: target,
                            color: color,
                            width: width,
                            dashes: dashes,
                            smooth: smooth,
                            arrows: { to: { enabled: false } },
                            title: edgeType === 'switch_link'
                                ? `${formatSwitchLabel(source)} -- ${formatSwitchLabel(target)}`
                                : `${source} -- ${target}`,
                            data: safeEdgeData,
                            originalColor: color,
                            originalWidth: width,
                            originalDashes: dashes,
                            originalShadow: {
                                enabled: true,
                                color: 'rgba(0,0,0,0.3)',
                                size: 5
                            }
                        });

                        addedEdges++;
                    } catch (err) {
                        console.error('添加边失败:', edgeObj, err);
                    }
                });

                debugLog('已添加边数:', addedEdges, '/', renderEdges.length);

                syncDataSet(nodes, desiredNodes);
                syncDataSet(edges, desiredEdges);
                switchLinkEdgeIdsByKey = nextSwitchLinkEdgeIdsByKey;

                const topologySignature = computeTopologySignature(data);
                currentSwitchDomainMap = renderData.switchDomainMap || {};
                if (topologySignature !== lastLayoutSignature) {
                    debugLog('开始应用自定义分层布局...');
                    applyCompactLayout(renderNodes, currentSwitchDomainMap, renderEdges);
                    lastLayoutSignature = topologySignature;

                    fitInitialTopologyOnce();
                }
                lastTopologySignature = topologySignature;

                // 上一帧存在、本帧消失的交换机间链路：保留 3 秒红/橙闪烁提示
                prevSwitchLinkMap.forEach(function(pair, key) {
                    if (newSwitchLinkKeys.has(key)) return;
                    if (!nodes.get(pair.from) || !nodes.get(pair.to)) return;
                    const phantomId = 'phantom-sl-' + Date.now() + '-' + Math.random().toString(36).slice(2, 9);
                    edges.add({
                        id: phantomId,
                        from: pair.from,
                        to: pair.to,
                        color: { color: '#ef4444', highlight: '#f87171', hover: '#fca5a5' },
                        width: 5,
                        dashes: [8, 4],
                        smooth: { type: 'curvedCW', roundness: 0.22 },
                        arrows: { to: { enabled: false } },
                        title: '链路已断开（闪烁3秒）',
                        data: { edge_type: 'switch_link_removal_alert', phantom_removal: true }
                    });
                    startLinkRemovalBlink(phantomId);
                });
                applyRouteSessionHighlight();

                debugLog('拓扑布局完成');
            } catch (err) {
                console.error('updateNetwork失败:', err);
            }
        }

        // 自定义分层布局函数
        function applyCustomLayout() {
            try {
                console.log('计算自定义布局...');

                // 收集各层节点（使用nodeType属性而不是shape）
                const rootNodes = [];
                const controllerNodes = [];
                const switchNodes = [];
                const hostNodes = [];

                nodes.get().forEach(node => {
                    const nodeType = node.nodeType || 'unknown';
                    if (node.id === 'RootController' || nodeType === 'root_controller') {
                        rootNodes.push(node);
                    } else if (nodeType === 'controller') {
                        controllerNodes.push(node);
                    } else if (nodeType === 'switch') {
                        switchNodes.push(node);
                    } else if (nodeType === 'host') {
                        hostNodes.push(node);
                    }
                });

                console.log(`节点分布 - 根:${rootNodes.length}, 从控:${controllerNodes.length}, 交换机:${switchNodes.length}, 主机:${hostNodes.length}`);

                // 构建交换机-主机组（交换机与其连接的主机作为一个整体）
                const switchGroups = {};  // {switchId: [hostIds]}

                // 找出每个交换机连接的主机
                edges.get().forEach(edge => {
                    const edgeData = edge.data || {};
                    const fromNode = nodes.get(edge.from);
                    const toNode = nodes.get(edge.to);

                    // 检查是否是主机-交换机连接
                    if (edgeData.edge_type === 'host_switch' ||
                        (fromNode && toNode &&
                         ((fromNode.nodeType === 'switch' && toNode.nodeType === 'host') ||
                          (fromNode.nodeType === 'host' && toNode.nodeType === 'switch')))) {

                        const switchId = (fromNode && fromNode.nodeType === 'switch') ? edge.from : edge.to;
                        const hostId = (fromNode && fromNode.nodeType === 'host') ? edge.from : edge.to;

                        if (switchId && hostId) {
                            if (!switchGroups[switchId]) {
                                switchGroups[switchId] = [];
                            }
                            if (!switchGroups[switchId].includes(hostId)) {
                                switchGroups[switchId].push(hostId);
                            }
                        }
                    }
                });

                console.log('交换机-主机组:', switchGroups);

                // 布局参数（可调整以获得最佳视觉效果）
                const canvasWidth = 2400;      // 画布宽度
                const canvasHeight = 1400;     // 画布高度
                const layerHeight = 350;       // 层与层之间的垂直间距
                const nodeSpacing = 250;       // 同一层节点之间的水平间距
                const maxNodesPerRow = 10;     // 每行最多节点数（超过则分多行）
                const rowSpacing = 200;        // 多行时的行间距
                const hostOffset = 120;        // 主机相对于交换机的垂直偏移

                // ========== 第0层：根控制器 ==========
                // 位置：顶部中心
                const rootY = 0;
                rootNodes.forEach((node, index) => {
                    console.log(`放置根控制器: ${node.id} at (${canvasWidth/2}, ${rootY})`);
                    nodes.update({
                        id: node.id,
                        x: canvasWidth / 2,
                        y: rootY,
                        fixed: true
                    });
                });

                // ========== 第1层：从控制器 ==========
                // 位置：第二层，水平等间距排列，超过maxNodesPerRow则分多行
                const controllerY = rootY + layerHeight;
                const controllerCount = controllerNodes.length;
                const controllerRowCount = Math.ceil(controllerCount / maxNodesPerRow);

                console.log(`放置 ${controllerCount} 个从控制器，分 ${controllerRowCount} 行`);

                controllerNodes.forEach((node, index) => {
                    const rowIndex = Math.floor(index / maxNodesPerRow);
                    const colIndex = index % maxNodesPerRow;
                    const nodesInRow = Math.min(maxNodesPerRow, controllerCount - rowIndex * maxNodesPerRow);

                    // 计算该行的起始位置（居中）
                    const rowWidth = (nodesInRow - 1) * nodeSpacing;
                    const startX = (canvasWidth - rowWidth) / 2;
                    const x = startX + colIndex * nodeSpacing;
                    const y = controllerY + rowIndex * rowSpacing;

                    console.log(`  从控 ${index}: ${node.id} at (${x}, ${y})`);

                    nodes.update({
                        id: node.id,
                        x: x,
                        y: y,
                        fixed: true
                    });
                });

                // ========== 第2层：交换机-主机组 ==========
                // 策略：交换机与其连接的主机视为一个组，组作为整体水平排列
                // 位置：交换机在上，主机在交换机正下方（hostOffset距离）
                const switchLayerY = controllerY + layerHeight + (controllerRowCount > 1 ? rowSpacing : 0);

                // 创建组列表（每个组包含一个交换机和其主机）
                const groups = [];
                const assignedHosts = new Set();

                // 为每个交换机创建组
                switchNodes.forEach(switchNode => {
                    const group = {
                        switch: switchNode,
                        hosts: switchGroups[switchNode.id] || []
                    };
                    groups.push(group);

                    // 标记已分配的主机
                    group.hosts.forEach(hostId => assignedHosts.add(hostId));
                });

                // 添加未分配的主机为独立组（没有连接到任何交换机的主机）
                hostNodes.forEach(hostNode => {
                    if (!assignedHosts.has(hostNode.id)) {
                        groups.push({
                            switch: null,
                            hosts: [hostNode.id]
                        });
                    }
                });

                console.log(`共 ${groups.length} 个交换机-主机组`);

                // 布局组（支持多行，每行居中等间距排列）
                const groupCount = groups.length;
                const groupRowCount = Math.ceil(groupCount / maxNodesPerRow);

                console.log(`开始放置 ${groupCount} 个组，分 ${groupRowCount} 行`);

                groups.forEach((group, index) => {
                    // 计算组在第几行、第几列
                    const rowIndex = Math.floor(index / maxNodesPerRow);
                    const colIndex = index % maxNodesPerRow;
                    const groupsInRow = Math.min(maxNodesPerRow, groupCount - rowIndex * maxNodesPerRow);

                    // 计算该行的起始X坐标（使该行居中）
                    const rowWidth = (groupsInRow - 1) * nodeSpacing;
                    const startX = (canvasWidth - rowWidth) / 2;
                    const groupX = startX + colIndex * nodeSpacing;
                    const groupBaseY = switchLayerY + rowIndex * (rowSpacing + hostOffset);

                    // 放置交换机（组的上部）
                    if (group.switch) {
                        console.log(`  组 ${index}: 交换机 ${group.switch.id} at (${groupX}, ${groupBaseY}), 主机数: ${group.hosts.length}`);
                        nodes.update({
                            id: group.switch.id,
                            x: groupX,
                            y: groupBaseY,
                            fixed: true
                        });
                    }

                    // 放置主机（在交换机下方，作为一个整体）
                    const hostCount = group.hosts.length;
                    if (hostCount > 0) {
                        if (hostCount === 1) {
                            // 单个主机：直接在交换机正下方
                            nodes.update({
                                id: group.hosts[0],
                                x: groupX,
                                y: groupBaseY + hostOffset,
                                fixed: true
                            });
                        } else {
                            // 多个主机：以交换机为中心水平分布
                            const hostSpacing = 80;
                            const hostRowWidth = (hostCount - 1) * hostSpacing;
                            const hostStartX = groupX - hostRowWidth / 2;

                            group.hosts.forEach((hostId, hostIndex) => {
                                const hostX = hostStartX + hostIndex * hostSpacing;
                                const hostY = groupBaseY + hostOffset;

                                nodes.update({
                                    id: hostId,
                                    x: hostX,
                                    y: hostY,
                                    fixed: true
                                });
                            });
                        }
                    }
                });

                console.log('自定义布局应用完成');

            } catch (err) {
                console.error('应用自定义布局失败:', err);
            }
        }

        // 更新统计信息
        async function updateStatistics() {
            try {
                const response = await fetch('/api/statistics');
                const stats = await response.json();

                // 计算全局指标（简化计算）
                const totalThroughput = (stats.switches || 0) * 100; // 假设每个交换机100Mbps
                const avgLatency = 10 + Math.floor(Math.random() * 10); // 模拟延迟

                document.getElementById('metric-throughput').textContent = totalThroughput + ' Mbps';
                document.getElementById('metric-latency').textContent = avgLatency + ' ms';
            } catch (error) {
                console.error('获取统计信息失败:', error);
            }
        }

        // 测试API连接
        async function testAPI() {
            console.log('=== 开始API测试 ===');

            // 测试健康检查
            try {
                console.log('测试 /api/health...');
                const healthResp = await fetch('/api/health');
                const healthData = await healthResp.json();
                console.log('✓ 健康检查成功:', healthData);
                alert('API连接正常！\\n控制器数: ' + healthData.controllers + '\\n图节点数: ' + healthData.graph_nodes + '\\n图边数: ' + healthData.graph_edges);
            } catch (error) {
                console.error('✗ 健康检查失败:', error);
                alert('API连接失败！\\n请检查：\\n1. 根控制器是否运行\\n2. 浏览器控制台查看详细错误\\n3. 确认端口5000未被占用');
                return;
            }

            // 测试图数据
            try {
                console.log('测试 /api/graph...');
                const graphResp = await fetch('/api/graph');
                const graphData = await graphResp.json();
                console.log('✓ 图数据获取成功:', graphData);
                console.log(`  节点数: ${graphData.nodes.length}`);
                console.log(`  边数: ${graphData.edges.length}`);
            } catch (error) {
                console.error('✗ 图数据获取失败:', error);
            }

            // 测试统计信息
            try {
                console.log('测试 /api/statistics...');
                const statsResp = await fetch('/api/statistics');
                const statsData = await statsResp.json();
                console.log('✓ 统计信息获取成功:', statsData);
            } catch (error) {
                console.error('✗ 统计信息获取失败:', error);
            }

            console.log('=== API测试完成 ===');
        }

        // 显示节点信息
        function showEdgeInfo(edgeId) {
            const edge = edges.get(edgeId);
            if (!edge) return;
            currentSelectedSwitchId = null;

            const edgeData = getEdgeMetadata(edgeId, edge);
            const fromNode = nodes.get(edge.from);
            const toNode = nodes.get(edge.to);
            const srcId = fromNode ? fromNode.id : edge.from;
            const dstId = toNode ? toNode.id : edge.to;
            const srcLabel = formatEndpointLabel(fromNode, edge.from);
            const dstLabel = formatEndpointLabel(toNode, edge.to);

            const sidebarTitle = document.getElementById('sidebar-title');
            const sidebarSubtitle = document.getElementById('sidebar-subtitle');
            const sidebarIcon = document.getElementById('sidebar-icon');
            const sidebarContent = document.getElementById('sidebar-content');

            sidebarTitle.textContent = 'Switch Link';
            sidebarSubtitle.textContent = srcLabel + ' <-> ' + dstLabel;
            sidebarIcon.className = 'sidebar-icon switch';

            const delayVal = edgeData.delay;
            const bwVal = (edgeData.bw !== undefined) ? edgeData.bw
                : ((edgeData.free_bandwith !== undefined) ? edgeData.free_bandwith : edgeData.free_bandwidth);
            const lossVal = (edgeData.loss !== undefined) ? edgeData.loss : edgeData.loss_rate;

            const fmtMetric = (v, unit) => {
                if (v === undefined || v === null || v === '') return 'N/A';
                const n = Number(v);
                if (Number.isFinite(n)) return n.toFixed(3) + ' ' + unit;
                return String(v) + ' ' + unit;
            };
            const fmtDelay = (v) => {
                if (v === undefined || v === null || v === '') return 'N/A';
                const n = Number(v);
                if (Number.isFinite(n)) {
                    // 后端多数场景以秒保存，前端优先展示毫秒便于观察
                    return (n * 1000).toFixed(3) + ' ms';
                }
                return String(v);
            };

            let html = '';
            html += '<div class="sidebar-section">';
            html += '<h3 class="section-title">Link Endpoints</h3>';
            html += '<div class="info-card">';
            html += createInfoRow('Source Switch', srcLabel);
            html += createInfoRow('Target Switch', dstLabel);
            html += createInfoRow('Source DPID', String(srcId));
            html += createInfoRow('Target DPID', String(dstId));
            if (edgeData.src_port !== undefined) {
                html += createInfoRow('Source Port', String(edgeData.src_port));
            }
            if (edgeData.dst_port !== undefined) {
                html += createInfoRow('Target Port', String(edgeData.dst_port));
            }
            html += '</div>';
            html += '</div>';

            html += '<div class="sidebar-section">';
            html += '<h3 class="section-title">Link Metrics</h3>';
            html += '<div class="info-card">';
            html += createInfoRow('Delay', fmtDelay(delayVal));
            html += createInfoRow('Bandwidth', fmtMetric(bwVal, 'Mbps'), true);
            html += createInfoRow('Packet Loss', fmtMetric(lossVal, '%'), false, false);
            html += createInfoRow('Edge Type', String(edgeData.edge_type || 'switch_link'));
            if (edgeData.source_domain || edgeData.target_domain) {
                html += createInfoRow('Domain Pair', String(edgeData.source_domain || '-') + ' <-> ' + String(edgeData.target_domain || '-'));
            }
            html += '</div>';
            html += '</div>';

            sidebarContent.innerHTML = html;
        }

        async function loadSwitchFlowsForSidebar(switchId, forceReload = false) {
            const existingNode = nodes.get(switchId);
            if (!existingNode) return;
            const existingData = existingNode.nodeData || {};
            if (!forceReload && Array.isArray(existingData.flow_table)) {
                return;
            }
            try {
                const response = await fetch('/api/switch/' + encodeURIComponent(String(switchId)) + '/flows');
                if (!response.ok) {
                    throw new Error('HTTP ' + response.status);
                }
                const payload = await response.json();
                const node = nodes.get(switchId);
                if (!node) return;
                const nodeData = Object.assign({}, node.nodeData || {});
                nodeData.flow_table = Array.isArray(payload.flows) ? payload.flows : [];
                nodeData.flow_count = payload.flow_count || nodeData.flow_table.length;
                nodes.update({ id: switchId, nodeData: nodeData });
                if (String(currentSelectedSwitchId) === String(switchId)) {
                    showNodeInfo(switchId);
                }
            } catch (error) {
                console.warn('加载交换机流表失败:', error);
                const node = nodes.get(switchId);
                if (!node) return;
                const nodeData = Object.assign({}, node.nodeData || {});
                nodeData.flow_table_error = String(error.message || error);
                nodes.update({ id: switchId, nodeData: nodeData });
                if (String(currentSelectedSwitchId) === String(switchId)) {
                    showNodeInfo(switchId);
                }
            }
        }

        async function refreshSelectedSwitchFlows() {
            if (!currentSelectedSwitchId || !nodes || !nodes.get(currentSelectedSwitchId)) {
                return;
            }
            await loadSwitchFlowsForSidebar(currentSelectedSwitchId, true);
        }

        // 显示节点信息
        function showNodeInfo(nodeId) {
            const node = nodes.get(nodeId);
            if (!node) return;

            const nodeType = node.nodeType || 'unknown';
            const nodeData = getNodeMetadata(nodeId, node);
            const connectionCounts = nodeData.connection_counts || {};
            currentSelectedSwitchId = (nodeType === 'switch') ? node.id : null;
            const displayLabel = getNodeDisplayLabel(node) || String(node.id);

            // 更新侧边栏标题
            const sidebarTitle = document.getElementById('sidebar-title');
            const sidebarSubtitle = document.getElementById('sidebar-subtitle');
            const sidebarIcon = document.getElementById('sidebar-icon');
            const sidebarContent = document.getElementById('sidebar-content');

            // 设置图标和标题
            let iconClass = '';
            let title = '';
            let subtitle = displayLabel;

            if (nodeType === 'root_controller') {
                iconClass = 'root';
                title = 'Root Controller';
            } else if (nodeType === 'controller') {
                iconClass = 'controller';
                title = 'Sub Controller';
            } else if (nodeType === 'switch') {
                iconClass = 'switch';
                title = displayLabel || 'OpenFlow Switch';
            } else if (nodeType === 'host') {
                iconClass = 'host';
                title = 'End Host';
            } else {
                iconClass = 'host';
                title = 'Unknown Node';
            }

            sidebarTitle.textContent = title;
            sidebarSubtitle.textContent = displayLabel;
            sidebarIcon.className = 'sidebar-icon ' + iconClass;

            // 生成内容HTML
            let html = '';

            // 基本信息部分
            html += '<div class="sidebar-section">';
            html += '<h3 class="section-title">Basic Info</h3>';
            html += '<div class="info-card">';

            if (nodeType === 'root_controller') {
                html += createInfoRow('IP Address', nodeData.ip || 'N/A');
                html += createInfoRow('Node Type', 'Root Controller');
                html += createInfoRow('Connected Controllers', (connectionCounts.controllers || 0).toString());
            } else if (nodeType === 'controller') {
                html += createInfoRow('IP Address', nodeData.ip || 'N/A');
                html += createInfoRow('Port', (nodeData.port || 'N/A').toString());
                html += createInfoRow('Node Type', 'Sub Controller');
                html += createInfoRow('Connected Switches', (connectionCounts.switches || 0).toString());
            } else if (nodeType === 'switch') {
                html += createInfoRow('Display Label', displayLabel || 'N/A');
                html += createInfoRow('IP Address', nodeData.ip || node.id || 'N/A');
                if (nodeData.gateway_ip) {
                    html += createInfoRow('Gateway IP', nodeData.gateway_ip);
                }
                html += createInfoRow('DPID', node.id || 'N/A');
                html += '<div class="divider"></div>';
                // 交换机实时指标（如果有）
                if (nodeData.throughput !== undefined) {
                    html += createInfoRow('Throughput', (nodeData.throughput || 0) + ' Mbps', true);
                }
                if (nodeData.latency !== undefined) {
                    html += createInfoRow('Latency', (nodeData.latency || 0) + ' ms');
                }
                if (nodeData.loss !== undefined) {
                    html += createInfoRow('Packet Loss', (nodeData.loss || 0) + '%', false, true);
                }
                html += createInfoRow('Connected Hosts', (connectionCounts.hosts || 0).toString());
            } else if (nodeType === 'host') {
                html += createInfoRow('IP Address', node.id || 'N/A');
                if (nodeData.mac) {
                    html += createInfoRow('MAC', nodeData.mac);
                }
                html += createInfoRow('Node Type', 'End Host');
            }

            html += '</div>';
            html += '</div>';

            // 流表部分（仅交换机）
            if (nodeType === 'switch') {
                html += '<div class="sidebar-section">';
                html += '<div style="display: flex; justify-content: space-between; align-items: center; margin-bottom: 12px;">';
                html += '<h3 class="section-title">Flow Tables</h3>';
                html += '<button class="btn-add-flow" onclick="showAddFlowModal()">';
                html += '<svg width="14" height="14" viewBox="0 0 24 24" fill="none" stroke="currentColor" stroke-width="2"><line x1="12" y1="5" x2="12" y2="19"/><line x1="5" y1="12" x2="19" y2="12"/></svg>';
                html += '添加规则';
                html += '</button>';
                html += '</div>';
                html += '<div class="flow-table">';

                const flowTable = Array.isArray(nodeData.flow_table) ? nodeData.flow_table : null;
                if (nodeData.flow_table_error) {
                    html += '<div class="empty-state" style="margin-top: 20px;">';
                    html += '<p style="font-size: 14px; color: #ef4444;">流表加载失败</p>';
                    html += '<p style="font-size: 12px; color: #64748b; margin-top: 4px;">' + sanitizeHtml(nodeData.flow_table_error) + '</p>';
                    html += '</div>';
                } else if (flowTable === null) {
                    html += '<div class="empty-state" style="margin-top: 20px;">';
                    html += '<p style="font-size: 14px; color: #94a3b8;">正在加载流表...</p>';
                    html += '<p style="font-size: 12px; color: #475569; margin-top: 4px;">共 ' + (nodeData.flow_count || 0) + ' 条规则</p>';
                    html += '</div>';
                    loadSwitchFlowsForSidebar(node.id);
                } else if (flowTable.length > 0) {
                    flowTable.forEach((flow, idx) => {
                        html += createFlowItem(flow, node.id, idx);
                    });
                } else {
                    html += '<div class="empty-state" style="margin-top: 20px;">';
                    html += '<svg class="empty-state-icon" viewBox="0 0 24 24" fill="none" stroke="currentColor" stroke-width="2">';
                    html += '<circle cx="12" cy="12" r="10"/>';
                    html += '<line x1="12" y1="8" x2="12" y2="12"/>';
                    html += '<line x1="12" y1="16" x2="12.01" y2="16"/>';
                    html += '</svg>';
                    html += '<p style="font-size: 14px; color: #64748b;">暂无流表规则</p>';
                    html += '<p style="font-size: 12px; color: #475569; margin-top: 4px;">点击上方按钮添加第一条规则</p>';
                    html += '</div>';
                }

                html += '</div>';
                html += '</div>';
            }

            sidebarContent.innerHTML = html;

            // 为删除按钮添加事件监听器
            const deleteButtons = sidebarContent.querySelectorAll('.flow-delete');
            deleteButtons.forEach(btn => {
                btn.addEventListener('click', function() {
                    const switchId = this.getAttribute('data-switch-id');
                    const flowId = this.getAttribute('data-flow-id');
                    deleteFlow(switchId, flowId);
                });
            });
        }

        // 创建信息行
        function createInfoRow(label, value, highlight = false, error = false) {
            // 转义HTML特殊字符
            const escapeHtml = (str) => {
                if (str === null || str === undefined) return '';
                return String(str).replace(/&/g, '&amp;').replace(/</g, '&lt;').replace(/>/g, '&gt;').replace(/"/g, '&quot;').replace(/'/g, '&#39;');
            };

            const safeLabel = escapeHtml(String(label));
            const safeValue = escapeHtml(String(value));
            let valueClass = 'info-value';
            if (highlight) valueClass += ' highlight';
            if (error) valueClass += ' error';
            return '<div class="info-row"><span class="info-label">' + safeLabel + '</span><span class="' + valueClass + '">' + safeValue + '</span></div>';
        }

        // 创建流表项
        function createFlowItem(flow, switchId, index) {
            // 转义特殊字符以避免XSS和语法错误
            const escapeHtml = (str) => {
                if (!str) return '';
                return String(str).replace(/&/g, '&amp;').replace(/</g, '&lt;').replace(/>/g, '&gt;').replace(/"/g, '&quot;').replace(/'/g, '&#39;');
            };

            const safeSwitchId = escapeHtml(String(switchId));
            const safeFlowId = escapeHtml(String(flow.id || index));
            const safePriority = escapeHtml(String(flow.priority || flow.pri || 'N/A'));
            const safeMatch = escapeHtml(String(flow.match || 'N/A'));
            const safeAction = escapeHtml(String(flow.action || 'N/A'));
            const safeFlowIdNum = Math.floor(flow.id || index);
            const safePackets = flow.packets || 0;

            let html = '<div class="flow-item">';
            html += '<div class="flow-header">';
            html += '<div style="display: flex; align-items: center; gap: 8px;">';
            html += '<span class="flow-priority">Pri: ' + safePriority + '</span>';
            html += '<span class="flow-status"></span>';
            html += '</div>';
            html += '<div class="flow-delete" data-switch-id="' + safeSwitchId + '" data-flow-id="' + safeFlowId + '">';
            html += '<svg width="14" height="14" viewBox="0 0 24 24" fill="none" stroke="currentColor" stroke-width="2">';
            html += '<polyline points="3 6 5 6 21 6"/><path d="M19 6v14a2 2 0 0 1-2 2H7a2 2 0 0 1-2-2V6m3 0V4a2 2 0 0 1 2-2h4a2 2 0 0 1 2 2v2"/>';
            html += '</svg>';
            html += '</div>';
            html += '</div>';
            html += '<div class="flow-details">';
            html += '<div class="flow-detail-row">';
            html += '<span class="flow-detail-label">Match:</span>';
            html += '<span class="flow-detail-value match" title="' + safeMatch + '">' + safeMatch + '</span>';
            html += '</div>';
            html += '<div class="flow-detail-row">';
            html += '<span class="flow-detail-label">Action:</span>';
            html += '<span class="flow-detail-value action">' + safeAction + '</span>';
            html += '</div>';
            html += '</div>';
            html += '<div class="flow-footer">';
            html += '<span>ID: ' + safeFlowIdNum + '</span>';
            html += '<div class="flow-packet-count">';
            html += '<svg width="12" height="12" viewBox="0 0 24 24" fill="none" stroke="currentColor" stroke-width="2">';
            html += '<polyline points="22 12 18 12 15 21 9 3 6 12 2 12"/>';
            html += '</svg>';
            html += '<span>' + safePackets + ' pkts</span>';
            html += '</div>';
            html += '</div>';
            html += '</div>';
            return html;
        }

        // 关闭侧边栏
        function closeSidebar() {
            document.getElementById('sidebar').style.display = 'none';
        }

        function showFlowFormError(message) {
            const box = document.getElementById('flow-form-error');
            if (!box) return;
            if (!message) {
                box.style.display = 'none';
                box.textContent = '';
                return;
            }
            box.style.display = 'block';
            box.textContent = message;
        }

        function isValidIPv4(ip) {
            const v = (ip || '').trim();
            if (!v) return true;
            const parts = v.split('.');
            if (parts.length !== 4) return false;
            for (let i = 0; i < parts.length; i++) {
                const n = Number(parts[i]);
                if (!Number.isInteger(n) || n < 0 || n > 255) return false;
            }
            return true;
        }

        function intOrNull(value) {
            if (value === '' || value === null || value === undefined) return null;
            const n = parseInt(value, 10);
            return Number.isNaN(n) ? null : n;
        }

        function buildMatchFromFields() {
            const match = { eth_type: 0x0800 };
            const inPort = intOrNull(document.getElementById('flow-in-port').value);
            const ipProto = intOrNull(document.getElementById('flow-ip-proto').value);
            const srcIp = (document.getElementById('flow-ipv4-src').value || '').trim();
            const dstIp = (document.getElementById('flow-ipv4-dst').value || '').trim();
            const l4Src = intOrNull(document.getElementById('flow-l4-src').value);
            const l4Dst = intOrNull(document.getElementById('flow-l4-dst').value);

            if (inPort !== null) match.in_port = inPort;
            if (srcIp) match.ipv4_src = srcIp;
            if (dstIp) match.ipv4_dst = dstIp;
            if (ipProto !== null) match.ip_proto = ipProto;

            if (l4Src !== null || l4Dst !== null) {
                const proto = (ipProto === 17) ? 17 : 6;
                match.ip_proto = proto;
                if (l4Src !== null) {
                    if (proto === 17) match.udp_src = l4Src;
                    else match.tcp_src = l4Src;
                }
                if (l4Dst !== null) {
                    if (proto === 17) match.udp_dst = l4Dst;
                    else match.tcp_dst = l4Dst;
                }
            }
            return match;
        }

        function populateMatchPreviewFromFields() {
            const preview = document.getElementById('flow-match-json');
            if (!preview) return;
            const match = buildMatchFromFields();
            preview.value = JSON.stringify(match, null, 2);
            showFlowFormError('');
        }

        function showAddFlowModal() {
            const switchId = currentSelectedSwitchId || document.getElementById('sidebar-subtitle').textContent;
            if (!switchId) {
                alert('请先选择交换机节点');
                return;
            }
            document.getElementById('flow-modal-switch-id').textContent = '交换机: ' + switchId;
            document.getElementById('flow-out-port').value = '';
            document.getElementById('flow-priority').value = '10';
            document.getElementById('flow-idle-timeout').value = '0';
            document.getElementById('flow-hard-timeout').value = '0';
            document.getElementById('flow-in-port').value = '';
            document.getElementById('flow-ip-proto').value = '';
            document.getElementById('flow-ipv4-src').value = '';
            document.getElementById('flow-ipv4-dst').value = '';
            document.getElementById('flow-l4-src').value = '';
            document.getElementById('flow-l4-dst').value = '';
            populateMatchPreviewFromFields();
            showFlowFormError('');
            document.getElementById('flow-modal-overlay').style.display = 'flex';
        }

        function closeAddFlowModal() {
            const overlay = document.getElementById('flow-modal-overlay');
            if (overlay) overlay.style.display = 'none';
            showFlowFormError('');
        }

        async function handleAddFlowSubmit(event) {
            event.preventDefault();

            const switchId = currentSelectedSwitchId || document.getElementById('sidebar-subtitle').textContent;
            if (!switchId) {
                showFlowFormError('未找到目标交换机，请重新选择交换机。');
                return;
            }

            const outPort = intOrNull(document.getElementById('flow-out-port').value);
            const priority = intOrNull(document.getElementById('flow-priority').value);
            const idleTimeout = intOrNull(document.getElementById('flow-idle-timeout').value);
            const hardTimeout = intOrNull(document.getElementById('flow-hard-timeout').value);
            const srcIp = (document.getElementById('flow-ipv4-src').value || '').trim();
            const dstIp = (document.getElementById('flow-ipv4-dst').value || '').trim();

            if (outPort === null || outPort <= 0) {
                showFlowFormError('输出端口 out_port 必须是大于 0 的整数。');
                return;
            }
            if (priority === null || priority < 0) {
                showFlowFormError('priority 必须是大于等于 0 的整数。');
                return;
            }
            if (idleTimeout === null || idleTimeout < 0 || hardTimeout === null || hardTimeout < 0) {
                showFlowFormError('idle_timeout / hard_timeout 必须是大于等于 0 的整数。');
                return;
            }
            if (!isValidIPv4(srcIp) || !isValidIPv4(dstIp)) {
                showFlowFormError('ipv4_src / ipv4_dst 格式不正确。');
                return;
            }

            let match = {};
            try {
                match = JSON.parse(document.getElementById('flow-match-json').value || '{}');
            } catch (err) {
                showFlowFormError('Match 预览 JSON 解析失败，请检查格式。');
                return;
            }
            if (!match || typeof match !== 'object' || Array.isArray(match)) {
                showFlowFormError('Match 必须是 JSON 对象。');
                return;
            }

            try {
                const resp = await fetch('/api/flows', {
                    method: 'POST',
                    headers: { 'Content-Type': 'application/json' },
                    body: JSON.stringify({
                        switch_id: switchId,
                        out_port: outPort,
                        priority: priority,
                        idle_timeout: idleTimeout,
                        hard_timeout: hardTimeout,
                        match: match
                    })
                });
                const result = await resp.json();
                if (!resp.ok || result.status !== 'ok') {
                    throw new Error(result.error || result.message || ('HTTP ' + resp.status));
                }
                closeAddFlowModal();
                await refreshTopology();
                await loadSwitchFlowsForSidebar(switchId, true);
                showNodeInfo(switchId);
                alert('流表下发请求已发送');
            } catch (err) {
                console.error('添加流表失败:', err);
                showFlowFormError('提交失败: ' + err.message);
            }
        }

        // 删除流表项
        async function deleteFlow(switchId, flowId) {
            if (!confirm('确定要删除这条流表规则吗？')) {
                return;
            }
            try {
                const resp = await fetch('/api/flows', {
                    method: 'DELETE',
                    headers: { 'Content-Type': 'application/json' },
                    body: JSON.stringify({
                        switch_id: switchId,
                        flow_id: flowId
                    })
                });
                const result = await resp.json();
                if (!resp.ok || result.status !== 'ok') {
                    throw new Error(result.error || result.message || ('HTTP ' + resp.status));
                }
                await refreshTopology();
                await loadSwitchFlowsForSidebar(switchId, true);
                showNodeInfo(switchId);
            } catch (err) {
                console.error('删除流表失败:', err);
                alert('删除流表失败: ' + err.message);
            }
        }

        // 自适应缩放
        function fitNetwork() {
            if (network) {
                network.fit({
                    animation: {
                        duration: 1000,
                        easingFunction: 'easeInOutQuad'
                    }
                });
            }
        }

        // 切换布局
        function changeLayout() {
            const layout = document.getElementById('layout-select').value;
            console.log('切换布局:', layout);

            let options = {};

            if (layout === 'custom') {
                // 自定义分层布局
                options = {
                    layout: {
                        hierarchical: { enabled: false }
                    },
                    physics: { enabled: false }
                };

                network.setOptions(options);

                // 释放所有节点的固定状态
                nodes.get().forEach(node => {
                    nodes.update({ id: node.id, fixed: false });
                });

                // 重新应用自定义布局
                setTimeout(() => {
                    applyCustomLayout();
                    fitNetwork();
                }, 100);

            } else if (layout === 'hierarchical') {
                // vis.js内置层次布局
                options = {
                    layout: {
                        hierarchical: {
                            enabled: true,
                            direction: 'UD',
                            sortMethod: 'directed',
                            levelSeparation: 200,
                            nodeSpacing: 180
                        }
                    },
                    physics: { enabled: false }
                };

                // 释放固定位置
                nodes.get().forEach(node => {
                    nodes.update({ id: node.id, fixed: false });
                });

                network.setOptions(options);
                setTimeout(fitNetwork, 500);

            } else if (layout === 'physics') {
                // 物理力导向布局
                options = {
                    layout: {
                        hierarchical: { enabled: false }
                    },
                    physics: {
                        enabled: true,
                        barnesHut: {
                            gravitationalConstant: -3000,
                            centralGravity: 0.3,
                            springLength: 250,
                            springConstant: 0.04
                        },
                        stabilization: {
                            iterations: 150
                        }
                    }
                };

                // 释放固定位置
                nodes.get().forEach(node => {
                    nodes.update({ id: node.id, fixed: false });
                });

                network.setOptions(options);

            } else if (layout === 'circle') {
                // 环形布局
                options = {
                    layout: {
                        hierarchical: { enabled: false }
                    },
                    physics: { enabled: false }
                };

                network.setOptions(options);

                // 手动设置环形布局
                const nodeIds = nodes.getIds();
                const radius = 400;
                const angleStep = (2 * Math.PI) / nodeIds.length;

                nodeIds.forEach((id, index) => {
                    const angle = index * angleStep - Math.PI / 2;  // 从顶部开始
                    const x = radius * Math.cos(angle);
                    const y = radius * Math.sin(angle);
                    nodes.update({ id: id, x: x, y: y, fixed: true });
                });

                setTimeout(fitNetwork, 100);
            }
        }

        // 页面加载完成后初始化
        console.log('脚本已加载');
        window.addEventListener('load', function() {
            console.log('页面load事件触发');
            initNetwork();
        });

        // 备用：DOMContentLoaded事件
        document.addEventListener('DOMContentLoaded', function() {
            console.log('DOMContentLoaded事件触发');
        });
    </script>
</body>
</html>

    '''
    return html
