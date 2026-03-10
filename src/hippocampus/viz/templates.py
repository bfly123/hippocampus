"""HTML templates for visualization."""

# HTML template header
HTML_HEADER = """<!DOCTYPE html>
<html lang="en">
<head>
    <meta charset="UTF-8">
    <meta name="viewport" content="width=device-width, initial-scale=1.0">
    <title>Hippocampus Visualization</title>
    <script src="https://cdn.jsdelivr.net/npm/echarts@5.4.3/dist/echarts.min.js"></script>
    <style>
        :root {
            --bg-app: #F8FAFC;
            --bg-card: #FFFFFF;
            --text-primary: #1E293B;
            --text-secondary: #64748B;
            --accent: #4F46E5;
            --shadow-sm: 0 1px 3px rgba(0,0,0,0.1);
            --shadow-md: 0 4px 6px -1px rgba(0,0,0,0.1), 0 2px 4px -1px rgba(0,0,0,0.06);
        }
        * {
            margin: 0;
            padding: 0;
            box-sizing: border-box;
        }
        body {
            font-family: 'Inter', system-ui, -apple-system, sans-serif;
            background-color: var(--bg-app);
            color: var(--text-primary);
            overflow: hidden;
        }
        #container {
            display: grid;
            grid-template-rows: 64px 1fr 200px;
            grid-template-columns: 1fr 340px;
            gap: 16px;
            padding: 16px;
            height: 100vh;
        }
        #main-view-wrapper, #sidebar, #trends, #toolbar {
            background: var(--bg-card);
            border-radius: 12px;
            box-shadow: var(--shadow-sm);
            border: 1px solid #E2E8F0;
            transition: box-shadow 0.2s;
        }
        #main-view-wrapper:hover, #sidebar:hover {
            box-shadow: var(--shadow-md);
        }
        #toolbar {
            grid-column: 1 / -1;
            display: flex;
            justify-content: space-between;
            align-items: center;
            padding: 0 24px;
        }
        #toolbar h1 {
            font-size: 18px;
            font-weight: 600;
            color: var(--text-primary);
            margin: 0;
        }
        #main-view-wrapper {
            background: white;
            border-radius: 8px;
            box-shadow: 0 2px 8px rgba(0,0,0,0.1);
            position: relative;
        }
        #main-view {
            width: 100%;
            height: 100%;
        }
        #sidebar {
            background: white;
            border-radius: 8px;
            box-shadow: 0 2px 8px rgba(0,0,0,0.1);
            padding: 20px;
            overflow-y: auto;
        }
        #trends {
            grid-column: 1 / -1;
            background: white;
            border-radius: 8px;
            box-shadow: 0 2px 8px rgba(0,0,0,0.1);
        }
        .btn {
            background: transparent;
            color: var(--text-secondary);
            border: 1px solid #CBD5E1;
            padding: 6px 16px;
            font-size: 13px;
            font-weight: 500;
            border-radius: 6px;
            transition: all 0.2s;
            cursor: pointer;
        }
        .btn:hover {
            background: #F1F5F9;
        }
        .btn.active {
            background: var(--accent);
            color: white;
            border-color: var(--accent);
            box-shadow: 0 2px 4px rgba(79, 70, 229, 0.3);
        }
        #sidebar {
            padding: 20px;
            overflow-y: auto;
        }
        #sidebar h2 {
            font-size: 14px;
            text-transform: uppercase;
            letter-spacing: 0.05em;
            color: var(--text-secondary);
            border-bottom: 1px solid #E2E8F0;
            padding-bottom: 12px;
            margin-bottom: 16px;
        }
        h2 {
            font-size: 18px;
            margin-bottom: 15px;
            color: #333;
        }
        .stat-item {
            margin-bottom: 10px;
            padding: 10px;
            background: #f9f9f9;
            border-radius: 4px;
        }
        .stat-label {
            font-size: 12px;
            color: #666;
        }
        .stat-value {
            font-size: 20px;
            font-weight: bold;
            color: #333;
        }
        .change-item {
            padding: 8px;
            margin-bottom: 6px;
            background: #F8FAFC;
            border-radius: 4px;
            font-size: 13px;
        }
    </style>
</head>
<body>
    <div id="container">
        <div id="toolbar">
            <h1 style="font-size: 20px; color: #333;">Hippocampus Visualization</h1>
            <div style="display: flex; gap: 8px;">
                <button class="btn active" onclick="switchView('modules', event)">Module Graph</button>
                <button class="btn" onclick="switchView('files-graph', event)">File Graph</button>
                <button class="btn" onclick="switchView('functions', event)">Function Graph</button>
                <button class="btn" onclick="switchView('files-tree', event)">File Tree</button>
            </div>
        </div>
        <div id="main-view-wrapper" style="position: relative;">
            <div id="main-view" style="width: 100%; height: 100%;"></div>
            <div id="breadcrumb" style="position: absolute; top: 0; left: 0; right: 0; z-index: 1000;
                                        padding: 8px 20px; background: rgba(248,250,252,0.95);
                                        border-bottom: 1px solid #e2e8f0; font-size: 13px; display: none;
                                        border-radius: 12px 12px 0 0;">
            </div>
            <button id="backButton" onclick="goBack()"
                    style="position: absolute; top: 44px; left: 20px; z-index: 1000;
                           background: white; border: 1px solid #e2e8f0; padding: 6px 14px;
                           border-radius: 6px; cursor: pointer; display: none;
                           box-shadow: 0 2px 4px rgba(0,0,0,0.1); font-size: 13px;">
                ⬅ Back
            </button>
        </div>
        <div id="sidebar">
            <h2>Details</h2>
            <div id="details-content">
                <p style="color: #999;">Click on a module or file to view details</p>
            </div>
        </div>
        <div id="trends"></div>
    </div>

    <script>
        // Data embedded from JSON files
        const INDEX_DATA = __INDEX_DATA__;
        const MODULES_GRAPH = __MODULES_GRAPH__;
        const FILES_GRAPH = __FILES_GRAPH__;
        const FUNCTIONS_GRAPH = __FUNCTIONS_GRAPH__;
        const FILES_TREEMAP = __FILES_TREEMAP__;
        const MODULES_TREEMAP = __MODULES_TREEMAP__;
        const STATS_PIE = __STATS_PIE__;
        const TRENDS = __TRENDS__;
        const SNAPSHOTS_DATA = __SNAPSHOTS_DATA__;

        // Initialize charts
        const mainChart = echarts.init(document.getElementById('main-view'));
        const trendsChart = echarts.init(document.getElementById('trends'));

        // Shared ECharts legend config for module role views
        const ROLE_LEGEND = {
            data: ['core', 'infra', 'interface', 'test', 'docs'],
            top: 10,
            right: 20,
            orient: 'vertical',
            itemGap: 10,
            textStyle: { color: '#475569', fontSize: 12 }
        };

        // Shared categories with colors for module role views
        const ROLE_CATEGORIES = [
            {name: 'core', itemStyle: {color: '#6366F1'}},
            {name: 'infra', itemStyle: {color: '#A855F7'}},
            {name: 'interface', itemStyle: {color: '#14B8A6'}},
            {name: 'test', itemStyle: {color: '#F59E0B'}},
            {name: 'docs', itemStyle: {color: '#94A3B8'}}
        ];

        let currentView = 'modules';
        let viewStack = []; // Navigation stack for back button
        let focusFile = null; // For function graph filtering

        // Switch view function
        function switchView(view, event, options = {}) {
            currentView = view;

            // Reset focus mode UI when switching views
            hideBreadcrumb();

            // Update button active states
            document.querySelectorAll('.btn').forEach(btn => btn.classList.remove('active'));

            // Find and activate the correct button based on view
            const viewButtonMap = {
                'modules': 0,
                'files-graph': 1,
                'functions': 2,
                'files-tree': 3
            };

            const buttonIndex = viewButtonMap[view];
            if (buttonIndex !== undefined) {
                const buttons = document.querySelectorAll('.btn');
                if (buttons[buttonIndex]) {
                    buttons[buttonIndex].classList.add('active');
                }
            }

            if (view === 'modules') {
                renderModulesGraph();
            } else if (view === 'files-graph') {
                renderFilesGraph(options.filterModule);
            } else if (view === 'functions') {
                focusFile = options.focusFile || null;
                renderFunctionsGraph(focusFile);
            } else if (view === 'files-tree') {
                renderFilesTreemap();
            }
        }

        // Render modules graph
        function renderModulesGraph() {
            // Always render static graph by default (shows real dependencies)
            renderStaticModulesGraph();
        }

        // Render static modules graph (fallback)
        function renderStaticModulesGraph() {
            const option = {
                title: { show: false },
                tooltip: {
                    backgroundColor: 'rgba(255, 255, 255, 0.9)',
                    borderColor: '#E2E8F0',
                    textStyle: { color: '#1E293B' },
                    padding: 12,
                    extraCssText: 'box-shadow: 0 4px 6px -1px rgba(0,0,0,0.1); backdrop-filter: blur(4px);',
                    formatter: function(params) {
                        if (params.dataType === 'node') {
                            const d = params.data;
                            return `<b>${d.name}</b><br/>` +
                                   `Role: ${d.role || d.category}<br/>` +
                                   `Score: ${d.core_score.toFixed(3)}<br/>` +
                                   `Files: ${d.file_count}<br/>` +
                                   `<i>${d.desc}</i>`;
                        }
                        return params.name;
                    }
                },
                legend: ROLE_LEGEND,
                series: [{
                    type: 'graph',
                    layout: 'none',
                    data: MODULES_GRAPH.nodes.map(n => ({
                        ...n,
                        x: MODULES_GRAPH.positions[n.id].x,
                        y: MODULES_GRAPH.positions[n.id].y,
                        symbolSize: 28 + (Math.sqrt(n.core_score) * 36)
                    })),
                    links: MODULES_GRAPH.links,
                    categories: MODULES_GRAPH.categories,
                    roam: true,
                    draggable: false,
                    edgeSymbol: ['none', 'arrow'],
                    edgeSymbolSize: [4, 8],
                    label: {
                        show: true,
                        position: 'right',
                        formatter: '{b}',
                        fontSize: 12,
                        fontWeight: 600,
                        color: '#0F172A',
                        distance: 6,
                        textBorderColor: '#FFFFFF',
                        textBorderWidth: 3
                    },
                    labelLayout: { hideOverlap: true },
                    lineStyle: {
                        color: '#94A3B8',
                        opacity: 0.4,
                        width: 1.5,
                        curveness: 0.2
                    },
                    emphasis: {
                        scale: true,
                        focus: 'adjacency',
                        lineStyle: {
                            width: 3,
                            color: '#475569',
                            opacity: 0.9
                        }
                    }
                }]
            };
            mainChart.setOption(option);

            // Add click event for module nodes
            mainChart.off('click');
            mainChart.on('click', function(params) {
                if (params.dataType === 'node') {
                    showModuleDetails(params.data);
                }
            });
        }

        // Render snapshot frame with animation
        function renderSnapshot(index) {
            const frame = SNAPSHOTS_DATA.frames[index];
            if (!frame) return;

            // Get role color helper (with tier fallback for old snapshots)
            function getRoleColor(role) {
                const colors = {
                    'core': '#6366F1',
                    'infra': '#A855F7',
                    'interface': '#14B8A6',
                    'test': '#F59E0B',
                    'docs': '#94A3B8'
                };
                if (colors[role]) return colors[role];
                // Fallback for old tier-based data
                const tierColors = {
                    'core': '#6366F1',
                    'secondary': '#0F766E',
                    'peripheral': '#94A3B8',
                    'unknown': '#F59E0B'
                };
                return tierColors[role] || '#94A3B8';
            }

            // Build nodes with precomputed positions
            const nodes = frame.modules.map(m => ({
                id: m.id,
                name: m.name,
                x: m.x,
                y: m.y,
                symbolSize: 28 + Math.sqrt(m.core_score) * 36,
                value: m.core_score,
                category: m.role || m.tier,
                role: m.role || m.tier,
                itemStyle: { color: getRoleColor(m.role || m.tier) },
                core_score: m.core_score,
                file_count: m.file_count,
                desc: ''
            }));

            const option = {
                title: { show: false },
                tooltip: {
                    backgroundColor: 'rgba(255, 255, 255, 0.9)',
                    borderColor: '#E2E8F0',
                    textStyle: { color: '#1E293B' },
                    padding: 12,
                    extraCssText: 'box-shadow: 0 4px 6px -1px rgba(0,0,0,0.1);',
                    formatter: function(params) {
                        if (params.dataType === 'node') {
                            const d = params.data;
                            return `<b>${d.name}</b><br/>` +
                                   `Role: ${d.role || d.category}<br/>` +
                                   `Score: ${d.core_score.toFixed(3)}<br/>` +
                                   `Files: ${d.file_count}`;
                        }
                        return params.name;
                    }
                },
                legend: ROLE_LEGEND,
                series: [{
                    id: 'modulesGraph',
                    type: 'graph',
                    layout: 'none',
                    coordinateSystem: null,
                    data: nodes,
                    links: frame.links || [],
                    categories: ROLE_CATEGORIES,
                    roam: true,
                    draggable: false,
                    edgeSymbol: ['none', 'arrow'],
                    edgeSymbolSize: [4, 8],
                    label: {
                        show: true,
                        position: 'right',
                        formatter: '{b}',
                        fontSize: 12,
                        fontWeight: 600,
                        color: '#0F172A',
                        distance: 6,
                        textBorderColor: '#FFFFFF',
                        textBorderWidth: 3
                    },
                    labelLayout: { hideOverlap: true },
                    universalTransition: {
                        enabled: true,
                        seriesKey: 'modulesGraph'
                    },
                    animationDurationUpdate: 600,
                    animationEasingUpdate: 'cubicOut'
                }]
            };

            mainChart.setOption(option, { lazyUpdate: true });

            // Bind click event for module nodes
            mainChart.off('click');
            mainChart.on('click', function(params) {
                if (params.dataType === 'node') {
                    showModuleDetails(params.data);
                }
            });
        }

        // Render files graph
        function renderFilesGraph(filterModule = null) {
            let graphData = FILES_GRAPH;

            // Filter by module if specified
            if (filterModule) {
                const filteredNodes = graphData.nodes.filter(n => n.module === filterModule);
                const nodeIds = new Set(filteredNodes.map(n => n.id));
                const filteredLinks = graphData.links.filter(l =>
                    nodeIds.has(l.source) && nodeIds.has(l.target)
                );
                graphData = {
                    nodes: filteredNodes,
                    links: filteredLinks,
                    categories: graphData.categories
                };
            }

            const option = {
                title: {
                    text: filterModule ? `Files in ${filterModule}` : 'File Dependencies',
                    left: 20,
                    top: 10,
                    textStyle: { fontSize: 16, color: '#333' }
                },
                tooltip: {
                    backgroundColor: 'rgba(255, 255, 255, 0.9)',
                    borderColor: '#E2E8F0',
                    textStyle: { color: '#1E293B' },
                    padding: 12,
                    formatter: function(params) {
                        if (params.dataType === 'node') {
                            const d = params.data;
                            return `<b>${d.name}</b><br/>` +
                                   `Module: ${d.module}<br/>` +
                                   `Language: ${d.lang}<br/>` +
                                   `Symbols: ${d.value}<br/>` +
                                   `<i>${d.desc}</i>`;
                        } else if (params.dataType === 'edge') {
                            return `${params.data.source} → ${params.data.target}`;
                        }
                        return params.name;
                    }
                },
                series: [{
                    type: 'graph',
                    layout: 'force',
                    data: graphData.nodes,
                    links: graphData.links,
                    categories: graphData.categories,
                    roam: true,
                    draggable: true,
                    edgeSymbol: ['none', 'arrow'],
                    edgeSymbolSize: [4, 8],
                    force: {
                        repulsion: 200,
                        edgeLength: 100,
                        gravity: 0.1
                    },
                    label: {
                        show: true,
                        position: 'right',
                        formatter: '{b}',
                        fontSize: 10
                    },
                    labelLayout: { hideOverlap: true },
                    emphasis: {
                        scale: true,
                        focus: 'adjacency',
                        lineStyle: {
                            width: 3,
                            opacity: 0.9
                        }
                    }
                }]
            };
            mainChart.setOption(option, true);

            // Add click event for file nodes
            mainChart.off('click');
            mainChart.on('click', function(params) {
                if (params.dataType === 'node') {
                    // Get module name from node data
                    const moduleId = params.data.module || 'unknown';
                    const moduleName = moduleId.replace('mod:', '');
                    showFileDetails(params.data, moduleName);
                }
            });
        }

        // Render functions graph
        function renderFunctionsGraph(focusFile = null) {
            let graphData = FUNCTIONS_GRAPH;

            // If focus file specified, filter to relevant functions
            if (focusFile && INDEX_DATA.function_dependencies) {
                const relevantFuncs = new Set();

                // Add functions in focus file
                for (const funcKey in INDEX_DATA.function_dependencies) {
                    const filePath = funcKey.split(':')[0];
                    if (filePath === focusFile) {
                        relevantFuncs.add(funcKey);
                        // Add targets
                        for (const dep of INDEX_DATA.function_dependencies[funcKey]) {
                            relevantFuncs.add(dep.target);
                        }
                    }
                }

                // Add functions that call into focus file
                for (const funcKey in INDEX_DATA.function_dependencies) {
                    for (const dep of INDEX_DATA.function_dependencies[funcKey]) {
                        const targetFile = dep.target.split(':')[0];
                        if (targetFile === focusFile) {
                            relevantFuncs.add(funcKey);
                            relevantFuncs.add(dep.target);
                        }
                    }
                }

                const filteredNodes = graphData.nodes.filter(n => relevantFuncs.has(n.id));
                const nodeIds = new Set(filteredNodes.map(n => n.id));
                const filteredLinks = graphData.links.filter(l =>
                    nodeIds.has(l.source) && nodeIds.has(l.target)
                );

                graphData = {
                    nodes: filteredNodes,
                    links: filteredLinks,
                    categories: graphData.categories
                };
            }

            const option = {
                title: {
                    text: focusFile ? `Functions in ${focusFile}` : 'Function Call Graph',
                    left: 20,
                    top: 10,
                    textStyle: { fontSize: 16, color: '#333' }
                },
                tooltip: {
                    backgroundColor: 'rgba(255, 255, 255, 0.9)',
                    borderColor: '#E2E8F0',
                    textStyle: { color: '#1E293B' },
                    padding: 12,
                    formatter: function(params) {
                        if (params.dataType === 'node') {
                            const d = params.data;
                            return `<b>${d.name}</b><br/>` +
                                   `File: ${d.file}<br/>` +
                                   `Module: ${d.module}`;
                        } else if (params.dataType === 'edge') {
                            const d = params.data;
                            return `${d.source} → ${d.target}<br/>Calls: ${d.value || 1}`;
                        }
                        return params.name;
                    }
                },
                series: [{
                    type: 'graph',
                    layout: 'force',
                    data: graphData.nodes,
                    links: graphData.links,
                    roam: true,
                    draggable: true,
                    edgeSymbol: ['none', 'arrow'],
                    edgeSymbolSize: [4, 8],
                    force: {
                        repulsion: 150,
                        edgeLength: 80,
                        gravity: 0.1
                    },
                    label: {
                        show: true,
                        position: 'right',
                        formatter: '{b}',
                        fontSize: 9
                    },
                    labelLayout: { hideOverlap: true },
                    emphasis: {
                        scale: true,
                        focus: 'adjacency',
                        lineStyle: {
                            width: 3,
                            opacity: 0.9
                        }
                    }
                }]
            };
            mainChart.setOption(option, true);

            // Add click event
            mainChart.off('click');
            mainChart.on('click', function(params) {
                if (params.dataType === 'node') {
                    showFunctionDetails(params.data);
                }
            });
        }

        // Render files treemap
        function renderFilesTreemap() {
            const option = {
                title: { text: 'File Tree Structure', left: 'center' },
                tooltip: {},
                series: [{
                    type: 'treemap',
                    data: [FILES_TREEMAP],
                    leafDepth: 2,
                    roam: false,
                    label: { show: true, formatter: '{b}' },
                    itemStyle: { borderColor: '#fff' }
                }]
            };
            mainChart.setOption(option);
        }

        // Render diff sidebar
        function renderDiffSidebar(index) {
            if (index === 0) {
                document.getElementById('details-content').innerHTML =
                    '<p style="color: #999;">Baseline snapshot (no previous comparison)</p>' +
                    '<p style="color: #666; font-size: 12px; margin-top: 10px;">💡 Click on a module to view details</p>';
                return;
            }

            const diff = SNAPSHOTS_DATA.diffs[index - 1];
            if (!diff) return;

            let html = '<h3 style="font-size: 16px; margin-bottom: 15px;">Changes from Previous Snapshot</h3>';
            html += '<p style="color: #666; font-size: 12px; margin-bottom: 15px;">💡 Click on a module to view details</p>';

            if (diff.added.length > 0) {
                html += '<h4 style="color: #10B981; margin-top: 15px; font-size: 14px;">🟢 Added Modules</h4>';
                diff.added.forEach(id => {
                    const module = SNAPSHOTS_DATA.frames[index].modules.find(m => m.id === id);
                    if (module) {
                        html += `<div class="change-item">${module.name}</div>`;
                    }
                });
            }

            if (diff.removed.length > 0) {
                html += '<h4 style="color: #EF4444; margin-top: 15px; font-size: 14px;">🔴 Removed Modules</h4>';
                diff.removed.forEach(id => {
                    html += `<div class="change-item">${id.replace('mod:', '')}</div>`;
                });
            }

            if (diff.changed.length > 0) {
                html += '<h4 style="color: #3B82F6; margin-top: 15px; font-size: 14px;">🔵 Changed Modules</h4>';
                diff.changed.forEach(change => {
                    const tierInfo = change.tier_change ? `<br><small>Tier: ${change.tier_change}</small>` : '';
                    const roleInfo = change.role_change ? `<br><small>Role: ${change.role_change}</small>` : '';
                    const scoreInfo = Math.abs(change.score_delta) > 0.01 ?
                        `<br><small>Score: ${change.score_delta > 0 ? '+' : ''}${change.score_delta.toFixed(3)}</small>` : '';
                    html += `<div class="change-item">
                        ${change.id.replace('mod:', '')}${roleInfo}${tierInfo}${scoreInfo}
                    </div>`;
                });
            }

            if (diff.added.length === 0 && diff.removed.length === 0 && diff.changed.length === 0) {
                html += '<p style="color: #999; margin-top: 15px;">No changes detected</p>';
            }

            document.getElementById('details-content').innerHTML = html;
        }

        // Render trends chart
        function renderTrends() {
            const option = {
                title: {
                    text: 'Historical Trends (Click to view snapshot)',
                    left: 'center',
                    top: 10,
                    textStyle: { fontSize: 14, color: '#64748B' }
                },
                tooltip: {
                    trigger: 'axis',
                    formatter: function(params) {
                        let result = params[0].name + '<br/>';
                        params.forEach(p => {
                            result += p.marker + p.seriesName + ': ' + p.value + '<br/>';
                        });
                        result += '<i style="color: #999;">Click to view this snapshot</i>';
                        return result;
                    }
                },
                legend: { data: ['Files', 'Modules'], bottom: 10 },
                grid: { left: 50, right: 50, top: 50, bottom: 50 },
                xAxis: {
                    type: 'category',
                    data: TRENDS.dates.map((d, i) => {
                        // Format date display
                        return d.substring(0, 13).replace('T', ' ');
                    })
                },
                yAxis: { type: 'value' },
                series: [
                    {
                        name: 'Files',
                        type: 'line',
                        data: TRENDS.file_counts,
                        smooth: true
                    },
                    {
                        name: 'Modules',
                        type: 'line',
                        data: TRENDS.module_counts,
                        smooth: true
                    }
                ]
            };
            trendsChart.setOption(option);

            // Add click event
            trendsChart.off('click');
            trendsChart.on('click', function(params) {
                if (params.componentType === 'series') {
                    const snapshotIndex = params.dataIndex;
                    if (SNAPSHOTS_DATA.frames[snapshotIndex]) {
                        renderSnapshot(snapshotIndex);
                        renderDiffSidebar(snapshotIndex);
                    }
                }
            });
        }

        // Show module details in sidebar
        function showModuleDetails(moduleData) {
            const moduleDeps = INDEX_DATA.module_dependencies || {};
            const myDeps = moduleDeps[moduleData.id] || [];

            // Get files for this module (handle both static and snapshot modes)
            let moduleFiles = [];
            if (moduleData.files && Array.isArray(moduleData.files)) {
                // Static mode: files are embedded in node data
                moduleFiles = moduleData.files;
            } else {
                // Snapshot mode: need to fetch from INDEX_DATA
                const allFiles = INDEX_DATA.files || {};
                const fileDeps = INDEX_DATA.file_dependencies || {};

                for (const [filePath, fileInfo] of Object.entries(allFiles)) {
                    if (fileInfo.module === moduleData.id) {
                        moduleFiles.push({
                            path: filePath,
                            name: fileInfo.name || filePath.split('/').pop(),
                            desc: fileInfo.desc || '',
                            signatures: fileInfo.signatures || [],
                            dependencies: fileDeps[filePath] || []
                        });
                    }
                }
            }

            // Breadcrumb navigation
            let html = `
                <div style="padding: 10px 0; margin-bottom: 15px; border-bottom: 1px solid #e5e7eb;">
                    <div style="font-size: 12px; color: #64748b;">
                        <span style="cursor: pointer; color: #3b82f6;" onclick="switchView('modules', event)">🏠 Home</span>
                        <span style="margin: 0 6px;">›</span>
                        <span style="color: #1e293b; font-weight: 600;">${moduleData.name}</span>
                    </div>
                </div>
                <h3 style="color: #333; margin-bottom: 10px;">${moduleData.name}</h3>
                <p style="color: #666; font-size: 14px; margin-bottom: 15px;">${moduleData.desc || ''}</p>
                <div class="stat-item">
                    <div class="stat-label">Role</div>
                    <div class="stat-value">${moduleData.role || moduleData.category}</div>
                </div>
                <div class="stat-item">
                    <div class="stat-label">Core Score</div>
                    <div class="stat-value">${moduleData.core_score.toFixed(3)}</div>
                </div>
                <div class="stat-item">
                    <div class="stat-label">Files</div>
                    <div class="stat-value">${moduleFiles.length}</div>
                </div>
            `;

            // Show module dependencies
            if (myDeps.length > 0) {
                html += `
                    <h4 style="margin-top: 20px; margin-bottom: 10px; color: #475569;">
                        Dependencies (${myDeps.length})
                    </h4>
                    <div style="margin-bottom: 15px;">
                `;
                myDeps.forEach(dep => {
                    const targetName = dep.target.replace('mod:', '');
                    html += `
                        <div style="padding: 6px 10px; margin-bottom: 4px; background: #f1f5f9;
                                    border-left: 3px solid #64748b; border-radius: 3px; font-size: 12px;">
                            <span style="color: #334155;">→ ${targetName}</span>
                            <span style="color: #94a3b8; margin-left: 8px;">(${dep.weight} imports)</span>
                        </div>
                    `;
                });
                html += '</div>';
            }

            // Show files in module
            html += `
                <h4 style="margin-top: 20px; margin-bottom: 10px; color: #475569;">
                    Files (${moduleFiles.length})
                </h4>
                <div style="max-height: 400px; overflow-y: auto;">
            `;

            moduleFiles.forEach(file => {
                const depCount = file.dependencies ? file.dependencies.length : 0;
                const sigCount = file.signatures ? file.signatures.length : 0;
                html += `
                    <div class="file-item" data-file-path="${file.path}"
                         style="padding: 10px; margin-bottom: 6px; background: #f9fafb;
                                border: 1px solid #e5e7eb; border-radius: 4px; cursor: pointer;
                                transition: all 0.2s;">
                        <div style="font-weight: 600; font-size: 13px; color: #1e293b; margin-bottom: 4px;">
                            📄 ${file.name}
                        </div>
                        <div style="font-size: 11px; color: #64748b; margin-bottom: 4px;">
                            ${file.desc || 'No description'}
                        </div>
                        <div style="font-size: 11px; color: #94a3b8;">
                            ${sigCount} symbols · ${depCount} dependencies
                        </div>
                    </div>
                `;
            });

            html += '</div>';
            document.getElementById('details-content').innerHTML = html;

            // Add hover effect and click event listeners to file items
            document.querySelectorAll('.file-item').forEach((item, index) => {
                item.addEventListener('mouseenter', function() {
                    this.style.background = '#e0f2fe';
                    this.style.borderColor = '#0ea5e9';
                });
                item.addEventListener('mouseleave', function() {
                    this.style.background = '#f9fafb';
                    this.style.borderColor = '#e5e7eb';
                });
                item.addEventListener('click', function() {
                    const filePath = this.getAttribute('data-file-path');
                    const fileData = moduleFiles.find(f => f.path === filePath);
                    if (fileData) {
                        showFileDetails(fileData, moduleData.name);
                    }
                });
            });
        }

        // Show file details with code signatures
        function showFileDetails(fileData, moduleName, options) {
            var opts = options || {};
            // Store current module in view stack for back navigation (skip when navigating back)
            if (!opts.skipPush) {
                viewStack.push({ type: 'module', name: moduleName });
            }

            // Breadcrumb navigation
            let html = `
                <div style="padding: 10px 0; margin-bottom: 15px; border-bottom: 1px solid #e5e7eb;">
                    <div style="font-size: 12px; color: #64748b;">
                        <span style="cursor: pointer; color: #3b82f6;" onclick="switchView('modules', event)">🏠 Home</span>
                        <span style="margin: 0 6px;">›</span>
                        <span id="breadcrumb-module" style="cursor: pointer; color: #3b82f6;">${moduleName}</span>
                        <span style="margin: 0 6px;">›</span>
                        <span style="color: #1e293b; font-weight: 600;">${fileData.name}</span>
                    </div>
                </div>
                <div style="display: flex; justify-content: space-between; align-items: start; margin-bottom: 15px;">
                    <div>
                        <h3 style="color: #333; margin-bottom: 5px;">📄 ${fileData.name}</h3>
                        <div style="font-size: 11px; color: #64748b;">${fileData.path}</div>
                    </div>
                    <button class="focus-file-btn" data-file-path="${fileData.path.replace(/"/g, '&quot;')}"
                            style="background: #eff6ff; color: #3b82f6; border: 1px solid #bfdbfe;
                                   padding: 6px 12px; border-radius: 6px; cursor: pointer; font-size: 12px;">
                        🔍 Focus Graph
                    </button>
                </div>
                <p style="color: #666; font-size: 14px; margin-bottom: 15px;">${fileData.desc || 'No description'}</p>
                <div class="stat-item">
                    <div class="stat-label">Path</div>
                    <div class="stat-value" style="font-size: 11px; word-break: break-all;">${fileData.path}</div>
                </div>
            `;

            // Show file dependencies
            if (fileData.dependencies && fileData.dependencies.length > 0) {
                html += `
                    <h4 style="margin-top: 20px; margin-bottom: 10px; color: #475569;">
                        Dependencies (${fileData.dependencies.length})
                    </h4>
                    <div style="max-height: 200px; overflow-y: auto; margin-bottom: 15px;">
                `;
                fileData.dependencies.forEach(dep => {
                    const depName = dep.split('/').pop();
                    html += `
                        <div style="padding: 6px 10px; margin-bottom: 4px; background: #fef3c7;
                                    border-left: 3px solid #f59e0b; border-radius: 3px; font-size: 11px;">
                            <div style="color: #92400e; font-weight: 500;">${depName}</div>
                            <div style="color: #b45309; font-size: 10px;">${dep}</div>
                        </div>
                    `;
                });
                html += '</div>';
            }

            // Show code signatures
            if (fileData.signatures && fileData.signatures.length > 0) {
                // Pre-build reverse index for incoming dependency lookup
                const funcDepsMap = INDEX_DATA.function_dependencies || {};
                const incomingTargets = new Set();
                for (const deps of Object.values(funcDepsMap)) {
                    for (const d of deps) {
                        incomingTargets.add(d.target);
                    }
                }

                html += `
                    <h4 style="margin-top: 20px; margin-bottom: 10px; color: #475569;">
                        Symbols (${fileData.signatures.length})
                    </h4>
                    <div style="max-height: 300px; overflow-y: auto;">
                `;

                fileData.signatures.forEach((sig, sigIndex) => {
                    const kindColor = {
                        'class': '#3b82f6',
                        'function': '#8b5cf6',
                        'method': '#ec4899',
                        'variable': '#10b981'
                    }[sig.kind] || '#6b7280';

                    const isFunction = sig.kind === 'function' || sig.kind === 'method';
                    const funcKey = `${fileData.path}:${sig.name}`;
                    const hasOutgoing = isFunction && funcDepsMap[funcKey];
                    const hasIncoming = isFunction && incomingTargets.has(funcKey);
                    const hasDeps = hasOutgoing || hasIncoming;

                    const clickableClass = isFunction ? 'symbol-row-clickable' : '';
                    const clickableAttr = isFunction ? `data-sig-index="${sigIndex}"` : '';

                    html += `
                        <div class="${clickableClass}" ${clickableAttr}
                             style="padding: 8px 10px; margin-bottom: 5px; background: #f9fafb;
                                    border-left: 3px solid ${kindColor}; border-radius: 4px; font-family: 'Courier New', monospace;
                                    ${isFunction ? 'cursor: pointer; transition: background 0.15s, border-color 0.15s;' : ''}">
                            <div style="display: flex; align-items: center; gap: 8px;">
                                <span style="color: ${kindColor}; font-weight: 600; font-size: 11px; text-transform: uppercase;">
                                    ${sig.kind}
                                </span>
                                <span style="color: #1e293b; font-weight: 500; font-size: 13px;">
                                    ${sig.name}
                                </span>
                                <span style="color: #94a3b8; font-size: 11px; margin-left: auto;">
                                    line ${sig.line}
                                </span>
                                ${hasDeps ? `
                                    <button class="focus-func-btn" data-func-key="${funcKey.replace(/"/g, '&quot;')}"
                                            style="background: none; border: none; cursor: pointer;
                                                   color: #3b82f6; font-size: 14px; padding: 0 4px;"
                                            title="View call graph">
                                        🕸️
                                    </button>
                                ` : ''}
                            </div>
                            ${sig.desc ? `<div style="color: #64748b; font-size: 11px; margin-top: 4px; font-family: system-ui;">${sig.desc}</div>` : ''}
                        </div>
                    `;
                });

                html += '</div>';
            } else {
                html += '<p style="color: #999; margin-top: 20px;">No symbols available</p>';
            }

            document.getElementById('details-content').innerHTML = html;

            // Add breadcrumb click handler for module name
            const breadcrumbModule = document.getElementById('breadcrumb-module');
            if (breadcrumbModule) {
                breadcrumbModule.addEventListener('click', function() {
                    const moduleNode = MODULES_GRAPH.nodes.find(n => n.name === moduleName);
                    if (moduleNode) {
                        viewStack.pop();
                        showModuleDetails(moduleNode);
                    }
                });
            }

            // Bind focus-file button via data attribute (safe from quote injection)
            const focusFileBtn = document.querySelector('.focus-file-btn');
            if (focusFileBtn) {
                focusFileBtn.addEventListener('click', function() {
                    focusFileGraph(this.getAttribute('data-file-path'));
                });
            }

            // Bind focus-func buttons via data attributes
            document.querySelectorAll('.focus-func-btn').forEach(btn => {
                btn.addEventListener('click', function(e) {
                    e.stopPropagation();
                    focusFunctionGraph(this.getAttribute('data-func-key'));
                });
            });

            // Bind clickable symbol rows (function/method) for sidebar drill-down
            document.querySelectorAll('.symbol-row-clickable').forEach(row => {
                row.addEventListener('mouseenter', function() {
                    this.style.background = '#e0f2fe';
                    this.style.borderLeftColor = '#0ea5e9';
                });
                row.addEventListener('mouseleave', function() {
                    this.style.background = '#f9fafb';
                    this.style.borderLeftColor = '';
                });
                row.addEventListener('click', function(e) {
                    // Don't trigger if the 🕸️ icon was clicked
                    if (e.target.closest('.focus-func-btn')) return;
                    const idx = parseInt(this.getAttribute('data-sig-index'), 10);
                    if (isNaN(idx)) return;
                    // Look up full metadata by index (handles duplicate names)
                    const sig = fileData.signatures[idx];
                    if (!sig) return;
                    const funcKey = `${fileData.path}:${sig.name}`;
                    const funcDataObj = {
                        id: funcKey,
                        name: sig.name,
                        file: fileData.path,
                        module: (INDEX_DATA.files[fileData.path] || {}).module || 'unknown',
                        kind: sig.kind || '',
                        line: sig.line,
                        desc: sig.desc || ''
                    };
                    showFunctionDetails(funcDataObj, fileData, moduleName);
                });
            });
        }

        // Show function details
        function showFunctionDetails(funcData, parentFileData, parentModuleName) {
            // Push file onto viewStack when drilling down from file details
            if (parentFileData) {
                viewStack.push({ type: 'file', fileData: parentFileData, moduleName: parentModuleName });
            }

            const funcKey = funcData.id;
            const funcDeps = INDEX_DATA.function_dependencies || {};
            const myDeps = funcDeps[funcKey] || [];

            // Resolve module name for breadcrumb
            const rawModule = parentModuleName || funcData.module || 'unknown';
            const displayModule = rawModule.replace('mod:', '');

            // Build breadcrumb: Home › Module › File › Function (full) or Home › Module › Function (from graph)
            let breadcrumbHtml = `
                <div style="padding: 10px 0; margin-bottom: 15px; border-bottom: 1px solid #e5e7eb;">
                    <div style="font-size: 12px; color: #64748b;">
                        <span style="cursor: pointer; color: #3b82f6;" onclick="switchView('modules', event)">🏠 Home</span>
                        <span style="margin: 0 6px;">›</span>
                        <span id="breadcrumb-func-module" style="cursor: pointer; color: #3b82f6;">${displayModule}</span>
            `;
            if (parentFileData) {
                breadcrumbHtml += `
                        <span style="margin: 0 6px;">›</span>
                        <span id="breadcrumb-func-file" style="cursor: pointer; color: #3b82f6;">${parentFileData.name}</span>
                `;
            }
            breadcrumbHtml += `
                        <span style="margin: 0 6px;">›</span>
                        <span style="color: #1e293b; font-weight: 600;">${funcData.name}</span>
                    </div>
                </div>
            `;

            let html = breadcrumbHtml;
            html += `
                <div style="display: flex; justify-content: space-between; align-items: start; margin-bottom: 15px;">
                    <h3 style="color: #333; margin: 0;">⚡ ${funcData.name}</h3>
                    <button class="focus-func-detail-btn" data-func-key="${funcKey.replace(/"/g, '&quot;')}"
                            style="background: #eff6ff; color: #3b82f6; border: 1px solid #bfdbfe;
                                   padding: 6px 12px; border-radius: 6px; cursor: pointer; font-size: 12px;
                                   white-space: nowrap; flex-shrink: 0;">
                        🕸️ Focus Graph
                    </button>
                </div>
            `;

            // Kind badge
            const kind = funcData.kind || '';
            if (kind) {
                const kindColor = {'function': '#8b5cf6', 'method': '#ec4899', 'class': '#3b82f6'}[kind] || '#6b7280';
                html += `
                    <div style="margin-bottom: 12px;">
                        <span style="display: inline-block; background: ${kindColor}20; color: ${kindColor};
                                     padding: 2px 8px; border-radius: 4px; font-size: 11px; font-weight: 600;
                                     text-transform: uppercase;">${kind}</span>
                    </div>
                `;
            }

            // Description
            const desc = funcData.desc || '';
            if (desc) {
                html += `<p style="color: #666; font-size: 13px; margin-bottom: 15px;">${desc}</p>`;
            }

            html += `
                <div class="stat-item">
                    <div class="stat-label">File</div>
                    <div class="stat-value" style="font-size: 11px; word-break: break-all;">${funcData.file}</div>
                </div>
                <div class="stat-item">
                    <div class="stat-label">Module</div>
                    <div class="stat-value">${displayModule}</div>
                </div>
            `;

            if (funcData.line) {
                html += `
                    <div class="stat-item">
                        <div class="stat-label">Line</div>
                        <div class="stat-value">${funcData.line}</div>
                    </div>
                `;
            }

            // Show function calls
            if (myDeps.length > 0) {
                html += `
                    <h4 style="margin-top: 20px; margin-bottom: 10px; color: #475569;">
                        Calls (${myDeps.length})
                    </h4>
                    <div style="margin-bottom: 15px;">
                `;
                myDeps.forEach(dep => {
                    const targetParts = dep.target.split(':');
                    const targetFunc = targetParts[1] || dep.target;
                    const targetFile = targetParts[0] || '';
                    html += `
                        <div style="padding: 6px 10px; margin-bottom: 4px; background: #f1f5f9;
                                    border-left: 3px solid #64748b; border-radius: 3px; font-size: 12px;">
                            <span style="color: #334155;">→ ${targetFunc}</span>
                            <span style="color: #94a3b8; margin-left: 8px;">(${dep.weight || 1}x)</span>
                            <div style="font-size: 10px; color: #94a3b8; margin-top: 2px;">${targetFile}</div>
                        </div>
                    `;
                });
                html += '</div>';
            }

            // Find callers (functions that call this one)
            const callers = [];
            for (const [callerKey, deps] of Object.entries(funcDeps)) {
                for (const dep of deps) {
                    if (dep.target === funcKey) {
                        const callerParts = callerKey.split(':');
                        callers.push({
                            name: callerParts[1] || callerKey,
                            file: callerParts[0] || '',
                            weight: dep.weight || 1
                        });
                    }
                }
            }

            if (callers.length > 0) {
                html += `
                    <h4 style="margin-top: 20px; margin-bottom: 10px; color: #475569;">
                        Called By (${callers.length})
                    </h4>
                    <div style="margin-bottom: 15px;">
                `;
                callers.forEach(caller => {
                    html += `
                        <div style="padding: 6px 10px; margin-bottom: 4px; background: #fef3c7;
                                    border-left: 3px solid #f59e0b; border-radius: 3px; font-size: 12px;">
                            <span style="color: #92400e;">← ${caller.name}</span>
                            <span style="color: #d97706; margin-left: 8px;">(${caller.weight}x)</span>
                            <div style="font-size: 10px; color: #d97706; margin-top: 2px;">${caller.file}</div>
                        </div>
                    `;
                });
                html += '</div>';
            }

            document.getElementById('details-content').innerHTML = html;

            // Bind breadcrumb click: Module → go back to module details
            const bcModule = document.getElementById('breadcrumb-func-module');
            if (bcModule) {
                bcModule.addEventListener('click', function() {
                    const modId = rawModule.startsWith('mod:') ? rawModule : 'mod:' + rawModule;
                    const moduleNode = MODULES_GRAPH.nodes.find(n => n.id === modId || n.name === displayModule);
                    if (moduleNode) {
                        // Only pop if we pushed (sidebar drill-down path)
                        if (parentFileData) {
                            viewStack.pop(); // pop file entry pushed by showFunctionDetails
                            viewStack.pop(); // pop module entry pushed by showFileDetails
                        }
                        showModuleDetails(moduleNode);
                    }
                });
            }

            // Bind breadcrumb click: File → go back to file details
            const bcFile = document.getElementById('breadcrumb-func-file');
            if (bcFile && parentFileData) {
                bcFile.addEventListener('click', function() {
                    // Pop the file entry pushed by showFunctionDetails
                    viewStack.pop();
                    // Use skipPush to avoid re-pushing module onto viewStack
                    showFileDetails(parentFileData, displayModule, { skipPush: true });
                });
            }

            // Bind focus graph button for this function
            const focusFuncDetailBtn = document.querySelector('.focus-func-detail-btn');
            if (focusFuncDetailBtn) {
                focusFuncDetailBtn.addEventListener('click', function() {
                    focusFunctionGraph(this.getAttribute('data-func-key'));
                });
            }
        }

        // Focus on file's 1-hop dependency graph
        function focusFileGraph(centerFilePath) {
            // 1. Collect 1-hop neighbors
            const relatedNodes = new Set([centerFilePath]);
            const filteredLinks = [];

            FILES_GRAPH.links.forEach(link => {
                if (link.source === centerFilePath) {
                    relatedNodes.add(link.target);
                    filteredLinks.push({...link, direction: 'downstream'});
                }
                if (link.target === centerFilePath) {
                    relatedNodes.add(link.source);
                    filteredLinks.push({...link, direction: 'upstream'});
                }
            });

            // 2. Filter nodes (max 20)
            let filteredNodes = FILES_GRAPH.nodes.filter(n => relatedNodes.has(n.id));
            if (filteredNodes.length > 20) {
                const centerNode = filteredNodes.find(n => n.id === centerFilePath);
                const others = filteredNodes.filter(n => n.id !== centerFilePath)
                    .sort((a, b) => (b.value || 0) - (a.value || 0))
                    .slice(0, 19);
                filteredNodes = [centerNode, ...others];
            }

            // 3. Re-filter links after node truncation
            const keptNodeIds = new Set(filteredNodes.map(n => n.id));
            const validLinks = filteredLinks.filter(
                link => keptNodeIds.has(link.source) && keptNodeIds.has(link.target)
            );

            // 4. Handle empty neighbors
            if (filteredNodes.length <= 1) {
                const fileName = centerFilePath.split('/').pop();
                mainChart.setOption({
                    title: { text: `Focus: ${fileName}`, subtext: 'No connected files found', left: 20, top: 10, textStyle: { fontSize: 16, color: '#333' } },
                    series: [{ type: 'graph', layout: 'force', data: filteredNodes.map(n => ({...n, symbolSize: 50, itemStyle: { color: '#ef4444', borderColor: '#fee2e2', borderWidth: 3 }})), links: [], roam: true, label: { show: true, fontSize: 11 } }]
                }, true);
                mainChart.off('click');
                updateBreadcrumb(['Module Graph', `File: ${fileName}`]);
                showBackButton();
                return;
            }

            // 5. Highlight center node
            const styledNodes = filteredNodes.map(n => ({
                ...n,
                symbolSize: n.id === centerFilePath ? 50 : 20,
                itemStyle: n.id === centerFilePath ?
                    { color: '#ef4444', borderColor: '#fee2e2', borderWidth: 3 } :
                    n.itemStyle
            }));

            // 6. Style edges by direction
            const styledLinks = validLinks.map(link => ({
                ...link,
                lineStyle: {
                    width: link.direction === 'upstream' ? 2 : 1.5,
                    type: link.direction === 'upstream' ? 'dashed' : 'solid',
                    color: link.direction === 'upstream' ? '#ef4444' : '#3b82f6',
                    opacity: 0.6
                }
            }));

            // 5. Render graph
            const fileName = centerFilePath.split('/').pop();
            const option = {
                title: {
                    text: `Focus: ${fileName}`,
                    subtext: `${filteredNodes.length - 1} connected files`,
                    left: 20,
                    top: 10,
                    textStyle: { fontSize: 16, color: '#333' }
                },
                tooltip: {
                    backgroundColor: 'rgba(255, 255, 255, 0.9)',
                    borderColor: '#E2E8F0',
                    textStyle: { color: '#1E293B' },
                    padding: 12,
                    formatter: function(params) {
                        if (params.dataType === 'node') {
                            return `<b>${params.data.name}</b><br/>` +
                                   `Module: ${params.data.module}<br/>` +
                                   `Symbols: ${params.data.value}`;
                        } else if (params.dataType === 'edge') {
                            const dir = params.data.direction === 'upstream' ?
                                '→ imports' : '→ depends on';
                            return `${params.data.source.split('/').pop()} ${dir} ${params.data.target.split('/').pop()}`;
                        }
                    }
                },
                series: [{
                    type: 'graph',
                    layout: 'force',
                    data: styledNodes,
                    links: styledLinks,
                    roam: true,
                    draggable: true,
                    force: {
                        repulsion: 500,
                        edgeLength: 150,
                        gravity: 0.1
                    },
                    edgeSymbol: ['none', 'arrow'],
                    edgeSymbolSize: [4, 10],
                    label: {
                        show: true,
                        position: 'right',
                        fontSize: 11
                    },
                    emphasis: {
                        focus: 'adjacency',
                        lineStyle: { width: 3 }
                    }
                }]
            };

            mainChart.setOption(option, true);

            // Rebind click handler for focus graph nodes
            mainChart.off('click');
            mainChart.on('click', function(params) {
                if (params.dataType === 'node') {
                    const moduleId = params.data.module || 'unknown';
                    const moduleName = moduleId.replace('mod:', '');
                    showFileDetails(params.data, moduleName);
                }
            });

            // Update breadcrumb and back button
            updateBreadcrumb(['Module Graph', `File: ${fileName}`]);
            showBackButton();
        }

        // Focus on function's 1-hop call graph
        function focusFunctionGraph(centerFuncKey) {
            const funcDeps = INDEX_DATA.function_dependencies || {};

            // Check if data exists
            if (Object.keys(funcDeps).length === 0) {
                alert('Function dependencies data is empty. Please run: python -m hippocampus.cli index');
                return;
            }

            // 1. Collect 1-hop neighbors
            const relatedFuncs = new Set([centerFuncKey]);
            const filteredLinks = [];

            // Outgoing dependencies (functions this one calls)
            const outgoing = funcDeps[centerFuncKey] || [];
            outgoing.forEach(dep => {
                relatedFuncs.add(dep.target);
                filteredLinks.push({
                    source: centerFuncKey,
                    target: dep.target,
                    value: dep.weight,
                    direction: 'outgoing'
                });
            });

            // Incoming dependencies (functions that call this one)
            for (const [caller, deps] of Object.entries(funcDeps)) {
                deps.forEach(dep => {
                    if (dep.target === centerFuncKey) {
                        relatedFuncs.add(caller);
                        filteredLinks.push({
                            source: caller,
                            target: centerFuncKey,
                            value: dep.weight,
                            direction: 'incoming'
                        });
                    }
                });
            }

            // 2. Build nodes (limit 20)
            let nodes = Array.from(relatedFuncs).map(funcKey => {
                const [filePath, funcName] = funcKey.split(':');
                const fileInfo = INDEX_DATA.files[filePath] || {};

                return {
                    id: funcKey,
                    name: funcName,
                    file: filePath,
                    module: fileInfo.module || 'unknown',
                    symbolSize: funcKey === centerFuncKey ? 40 : 20,
                    itemStyle: funcKey === centerFuncKey ?
                        { color: '#ef4444', borderWidth: 3, borderColor: '#fee2e2' } :
                        { color: '#64748B' }
                };
            });

            if (nodes.length > 20) {
                const centerNode = nodes.find(n => n.id === centerFuncKey);
                const others = nodes.filter(n => n.id !== centerFuncKey).slice(0, 19);
                nodes = [centerNode, ...others];
            }

            // Re-filter links after node truncation
            const keptFuncIds = new Set(nodes.map(n => n.id));
            const validFuncLinks = filteredLinks.filter(
                link => keptFuncIds.has(link.source) && keptFuncIds.has(link.target)
            );

            // Handle empty neighbors
            if (nodes.length <= 1 && validFuncLinks.length === 0) {
                const funcName = centerFuncKey.split(':')[1];
                mainChart.setOption({
                    title: { text: `Function: ${funcName}`, subtext: 'No connected functions found', left: 20, top: 10, textStyle: { fontSize: 16, color: '#333' } },
                    series: [{ type: 'graph', layout: 'force', data: nodes, links: [], roam: true, label: { show: true, fontSize: 10 } }]
                }, true);
                mainChart.off('click');
                updateBreadcrumb(['Module Graph', `Function: ${funcName}`]);
                showBackButton();
                return;
            }

            // 3. Render
            const funcName = centerFuncKey.split(':')[1];
            const option = {
                title: {
                    text: `Function: ${funcName}`,
                    subtext: `${nodes.length - 1} related functions`,
                    left: 20,
                    top: 10,
                    textStyle: { fontSize: 16, color: '#333' }
                },
                tooltip: {
                    backgroundColor: 'rgba(255, 255, 255, 0.9)',
                    borderColor: '#E2E8F0',
                    textStyle: { color: '#1E293B' },
                    padding: 12,
                    formatter: function(params) {
                        if (params.dataType === 'node') {
                            return `<b>${params.data.name}</b><br/>` +
                                   `File: ${params.data.file}<br/>` +
                                   `Module: ${params.data.module}`;
                        } else if (params.dataType === 'edge') {
                            const srcName = params.data.source.split(':')[1];
                            const tgtName = params.data.target.split(':')[1];
                            return `${srcName} → ${tgtName}<br/>Calls: ${params.data.value}`;
                        }
                    }
                },
                series: [{
                    type: 'graph',
                    layout: 'force',
                    data: nodes,
                    links: validFuncLinks.map(link => ({
                        ...link,
                        lineStyle: {
                            width: Math.min(1 + link.value / 2, 4),
                            color: link.direction === 'incoming' ? '#ef4444' : '#3b82f6',
                            type: link.direction === 'incoming' ? 'dashed' : 'solid',
                            opacity: 0.6
                        }
                    })),
                    roam: true,
                    draggable: true,
                    force: {
                        repulsion: 400,
                        edgeLength: 120,
                        gravity: 0.1
                    },
                    edgeSymbol: ['none', 'arrow'],
                    edgeSymbolSize: [4, 8],
                    label: {
                        show: true,
                        fontSize: 10
                    },
                    emphasis: {
                        focus: 'adjacency',
                        lineStyle: { width: 3 }
                    }
                }]
            };

            mainChart.setOption(option, true);

            // Rebind click handler for function focus graph nodes
            mainChart.off('click');
            mainChart.on('click', function(params) {
                if (params.dataType === 'node') {
                    showFunctionDetails(params.data);
                }
            });

            updateBreadcrumb(['Module Graph', `Function: ${funcName}`]);
            showBackButton();
        }

        // Update breadcrumb navigation
        function updateBreadcrumb(path) {
            const breadcrumb = document.getElementById('breadcrumb');
            breadcrumb.style.display = 'block';

            let html = '<span style="cursor: pointer; color: #3b82f6;" onclick="switchView(\\x27modules\\x27, event); hideBreadcrumb();">🏠 Home</span>';

            path.forEach((item, index) => {
                html += ' <span style="color: #94a3b8;">›</span> ';
                if (index === path.length - 1) {
                    html += `<span style="color: #1e293b; font-weight: 600;">${item}</span>`;
                } else {
                    html += `<span style="cursor: pointer; color: #3b82f6;">${item}</span>`;
                }
            });

            breadcrumb.innerHTML = html;
        }

        // Hide breadcrumb and back button
        function hideBreadcrumb() {
            document.getElementById('breadcrumb').style.display = 'none';
            document.getElementById('backButton').style.display = 'none';
        }

        // Show back button
        function showBackButton() {
            document.getElementById('backButton').style.display = 'block';
        }

        // Go back to module view
        function goBack() {
            switchView('modules', null);
            hideBreadcrumb();
        }

        // Open file in editor (new tab with file:// protocol)
        function openFileInEditor(fileId) {
            // Normalize file ID
            const fileKey = fileId.startsWith('file:') ? fileId.slice(5) : fileId;
            const file = INDEX_DATA.files[fileKey];
            if (!file) {
                console.warn('File not found for editor:', fileId);
                return;
            }

            // Try to open with file:// protocol
            const fileUrl = 'file://' + window.location.pathname.split('/.hippocampus/')[0] + '/' + fileKey;
            window.open(fileUrl, '_blank');
        }

        // Load code preview
        async function loadCodePreview(fileId) {
            // Normalize file ID
            const fileKey = fileId.startsWith('file:') ? fileId.slice(5) : fileId;
            const file = INDEX_DATA.files[fileKey];
            if (!file) {
                console.warn('File not found for preview:', fileId);
                return;
            }

            const previewDiv = document.getElementById('code-preview-container');
            if (!previewDiv) {
                console.warn('Preview container not found');
                return;
            }
            previewDiv.innerHTML = '<p style="color: #999;">Loading...</p>';

            try {
                const fullPath = window.location.pathname.split('/.hippocampus/')[0] + '/' + fileKey;

                const response = await fetch('file://' + fullPath);
                const code = await response.text();

                // Show first 50 lines
                const lines = code.split('\\n').slice(0, 50);
                const preview = lines.join('\\n');
                const hasMore = code.split('\\n').length > 50;

                previewDiv.innerHTML = `
                    <pre style="background: #1E293B; color: #E2E8F0; padding: 12px; border-radius: 6px;
                                overflow-x: auto; font-size: 11px; line-height: 1.5; max-height: 400px; overflow-y: auto;">` +
                    escapeHtml(preview) +
                    (hasMore ? '\\n\\n... (truncated, open in editor for full content)' : '') +
                    `</pre>
                `;
            } catch (error) {
                previewDiv.innerHTML = `
                    <p style="color: #DC2626; background: #FEE2E2; padding: 10px; border-radius: 6px; font-size: 12px;">
                        ⚠️ Cannot load file preview. Browser security restrictions prevent loading local files.
                        <br><br>Click "Open in Editor" button to view the file.
                    </p>
                `;
            }
        }

        // Escape HTML for safe display
        function escapeHtml(text) {
            const div = document.createElement('div');
            div.textContent = text;
            return div.innerHTML;
        }

        // Render statistics
        function renderStats() {
            const stats = INDEX_DATA.stats || {};
            const html = `
                <div class="stat-item">
                    <div class="stat-label">Total Files</div>
                    <div class="stat-value">${stats.total_files || 0}</div>
                </div>
                <div class="stat-item">
                    <div class="stat-label">Total Modules</div>
                    <div class="stat-value">${stats.total_modules || 0}</div>
                </div>
                <div class="stat-item">
                    <div class="stat-label">Total Lines</div>
                    <div class="stat-value">${stats.total_lines || 0}</div>
                </div>
            `;
            document.getElementById('stats-content').innerHTML = html;
        }

        // Initialize on load
        window.onload = function() {
            renderModulesGraph();
            renderTrends();
        };

        // Handle window resize
        window.onresize = function() {
            mainChart.resize();
            trendsChart.resize();
        };
    </script>
</body>
</html>
"""
