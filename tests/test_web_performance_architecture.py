from pathlib import Path


ROOT = Path(__file__).resolve().parents[1]


def test_web_state_store_module_exists_and_versions_snapshots():
    text = (ROOT / "web_state_store.py").read_text(encoding="utf-8")

    assert "class WebStateStore" in text
    assert "topology_version" in text
    assert "route_sessions_version" in text
    assert "flow_versions" in text
    assert "get_graph_snapshot" in text


def test_web_api_serves_cached_graph_versions():
    text = (ROOT / "web_api.py").read_text(encoding="utf-8")

    assert "get_graph_snapshot" in text
    assert "'versions': snapshot.get('versions'" in text
    assert "server_agent.G.nodes(data=True)" not in text


def test_web_ui_page_disables_browser_cache():
    text = (ROOT / "web_api.py").read_text(encoding="utf-8")
    index_body = text[text.index("def index"):text.index("@app.route('/api/health'")]

    assert "make_response" in text
    assert "Cache-Control" in index_body
    assert "no-store" in index_body


def test_frontend_uses_incremental_graph_updates_and_layout_guard():
    text = (ROOT / "web_ui_html.py").read_text(encoding="utf-8")

    assert "function syncDataSet" in text
    assert "lastTopologySignature" in text
    assert "lastLayoutSignature" in text
    assert "nodes.clear()" not in text
    assert "edges.clear()" not in text
    assert "if (topologySignature !== lastLayoutSignature)" in text


def test_route_session_highlight_uses_delta_updates():
    text = (ROOT / "web_ui_html.py").read_text(encoding="utf-8")

    assert "lastHighlightedNodeIds" in text
    assert "lastHighlightedEdgeIds" in text
    body = text[text.index("function applyRouteSessionHighlight"):text.index("function selectRouteSessionById")]
    assert "nodes.get().forEach" not in body
    assert "edges.get().forEach" not in body


def test_server_agent_topology_update_does_not_dump_full_graph():
    text = (ROOT / "server_agent.py").read_text(encoding="utf-8")
    body = text[text.index("def update_graph"):text.index("def _lookup_host_mac")]

    assert "self.web_state.mark_topology_dirty" in body
    assert "print(f\"**********G" not in body
    assert "logger.info(f\"添加边" not in body
    assert "logger.info(f\"添加主机连接" not in body
def test_web_ui_avoids_optional_chaining_for_server_side_syntax_checks():
    text = (ROOT / "web_ui_html.py").read_text(encoding="utf-8")

    assert "?." not in text


def test_server_agent_topology_message_details_are_debug_only():
    text = (ROOT / "server_agent.py").read_text(encoding="utf-8")

    assert 'logger.info(f"链路详情:' not in text
    assert 'logger.info(f"主机详情:' not in text
def test_frontend_graph_refresh_ignores_metric_only_changes():
    text = (ROOT / "web_ui_html.py").read_text(encoding="utf-8")
    signature_body = text[text.index("function computeGraphSignature"):text.index("function computeTopologySignature")]
    refresh_body = text[text.index("async function refreshTopology"):text.index("function updateNetwork")]

    assert "nodeData.flow_count" not in signature_body
    assert "edgeData.delay" not in signature_body
    assert "edgeData.loss" not in signature_body
    assert "edgeData.bw" not in signature_body
    assert "refreshGraphMetadataCache(data)" in refresh_body
    assert "graphSignature !== lastGraphSignature" not in refresh_body
    assert "topologySignature !== lastTopologySignature" in refresh_body


def test_frontend_keeps_metric_updates_out_of_vis_dataset():
    text = (ROOT / "web_ui_html.py").read_text(encoding="utf-8")

    assert "let graphNodeDataById = new Map()" in text
    assert "let graphEdgeDataById = new Map()" in text
    assert "function refreshGraphMetadataCache" in text
    assert "function getEdgeMetadata" in text
    assert "const edgeData = getEdgeMetadata(edgeId, edge)" in text


def test_frontend_has_direct_hover_edge_handlers():
    text = (ROOT / "web_ui_html.py").read_text(encoding="utf-8")

    assert "network.on('hoverEdge'" in text
    assert "network.on('blurEdge'" in text
    assert "function setHoveredEdge" in text


def test_route_session_highlight_uses_current_graph_id_maps():
    text = (ROOT / "web_ui_html.py").read_text(encoding="utf-8")
    metadata_body = text[text.index("function refreshGraphMetadataCache"):text.index("function getNodeMetadata")]
    highlight_body = text[text.index("function applyRouteSessionHighlight"):text.index("function restoreEdgeVisual")]

    assert "let graphNodeIdsByKey = new Map()" in text
    assert "function getVisNodeId" in text
    assert "switchLinkEdgeIdsByKey = nextSwitchLinkEdgeIdsByKey" in metadata_body
    assert "getVisNodeId(nodeId)" in highlight_body


def test_route_session_highlight_uses_stable_edge_ids():
    text = (ROOT / "web_ui_html.py").read_text(encoding="utf-8")
    stable_edge_id_body = text[text.index("function stableEdgeId"):text.index("function refreshGraphMetadataCache")]

    assert "String(index)" not in stable_edge_id_body
    assert "stableEdgeId(edgeType, source, target)" in text
    assert "stableEdgeId(edgeType, source, target, index)" not in text


def test_topology_refresh_does_not_repeat_auto_fit():
    text = (ROOT / "web_ui_html.py").read_text(encoding="utf-8")
    update_body = text[text.index("function updateNetwork"):text.index("function applyCustomLayout")]

    assert "let hasAutoFitInitialTopology = false" in text
    assert "function fitInitialTopologyOnce" in text
    assert "network.fit({" not in update_body
    assert "fitInitialTopologyOnce()" in update_body


def test_hover_handlers_do_not_mutate_graph_dataset():
    text = (ROOT / "web_ui_html.py").read_text(encoding="utf-8")
    hover_body = text[text.index("function setHoveredEdge"):text.index("function selectRouteSessionById")]
    options_body = text[text.index("const options = {"):text.index("configure:")]

    assert "edges.update" not in hover_body
    assert "nodes.update" not in hover_body
    assert "chosen: false" in options_body
    assert "selectConnectedEdges: false" in options_body


def test_route_session_click_uses_event_delegation_and_selection_fallback():
    text = (ROOT / "web_ui_html.py").read_text(encoding="utf-8")
    panel_body = text[text.index("function updateRouteSessionsPanel"):text.index("function applyRouteSessionHighlight")]
    highlight_body = text[text.index("function applyRouteSessionHighlight"):text.index("function setHoveredEdge")]

    assert "onclick=\"selectRouteSessionById" not in panel_body
    assert "data-session-id" in panel_body
    assert "addEventListener('click'" in text
    assert "network.selectNodes" in highlight_body
    assert "network.selectEdges" in highlight_body
    assert "network.unselectAll" in highlight_body


def test_route_session_highlight_is_visually_distinct():
    text = (ROOT / "web_ui_html.py").read_text(encoding="utf-8")
    highlight_body = text[text.index("function applyRouteSessionHighlight"):text.index("function setHoveredEdge")]

    assert "#ecfeff" in highlight_body
    assert "#06b6d4" in highlight_body
    assert "shadow" in highlight_body
    assert "width: Math.max((edge.originalWidth || edge.width || 2) + 5.5, 9)" in highlight_body
    assert "dashes: [12, 4]" in highlight_body


def test_switch_labels_use_real_dpid_not_render_order():
    text = (ROOT / "web_ui_html.py").read_text(encoding="utf-8")
    update_body = text[text.index("function updateNetwork"):text.index("function applyCustomLayout")]

    assert "function formatSwitchLabel" in text
    assert "label = formatSwitchLabel(nodeId)" in update_body
    assert "label = 'SW' + nodeNumber" not in update_body
    assert "nodeNumber = getStableNodeNumber(nodeId)" in update_body


def test_sidebar_and_link_panels_use_same_display_identity():
    text = (ROOT / "web_ui_html.py").read_text(encoding="utf-8")
    node_body = text[text.index("function showNodeInfo"):text.index("function createInfoRow")]
    edge_body = text[text.index("function showEdgeInfo"):text.index("async function loadSwitchFlowsForSidebar")]

    assert "const displayLabel = getNodeDisplayLabel(node)" in node_body
    assert "sidebarSubtitle.textContent = displayLabel" in node_body
    assert "formatEndpointLabel(fromNode, edge.from)" in edge_body
    assert "formatEndpointLabel(toNode, edge.to)" in edge_body
    assert "createInfoRow('Source Switch', srcLabel)" in edge_body
    assert "createInfoRow('Target Switch', dstLabel)" in edge_body


def test_route_session_panel_formats_switch_path_labels():
    text = (ROOT / "web_ui_html.py").read_text(encoding="utf-8")
    panel_body = text[text.index("function updateRouteSessionsPanel"):text.index("function applyRouteSessionHighlight")]

    assert "function formatRouteSessionPath" in text
    assert "formatSwitchLabel" in text[text.index("function formatRouteSessionPath"):text.index("function sanitizeHtml")]
    assert "const pathText = formatRouteSessionPath(item)" in panel_body


def test_topology_has_auto_arrange_button():
    text = (ROOT / "web_ui_html.py").read_text(encoding="utf-8")
    header_body = text[text.index("<div class=\"header-controls\">"):text.index("</header>")]

    assert "arrange-topology-btn" in text
    assert "onclick=\"arrangeTopology()\"" in header_body
    assert "整理拓扑" in header_body


def test_auto_arrange_resets_manual_positions_and_reapplies_layout():
    text = (ROOT / "web_ui_html.py").read_text(encoding="utf-8")
    arrange_body = text[text.index("function arrangeTopology"):text.index("async function refreshTopology")]

    assert "switchManualPositions = {}" in arrange_body
    assert "localStorage.removeItem(compactPositionStorageKey)" in arrange_body
    assert "lastLayoutSignature = null" in arrange_body
    assert "applyCompactLayout(lastCompactLayoutData.nodes" in arrange_body
    assert "network.fit({" in arrange_body
    assert "applyRouteSessionHighlight()" in arrange_body
