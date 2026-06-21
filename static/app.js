const GRID_SIZE = 100;
const CANVAS_SIZE = 500;
const CELL_SIZE = CANVAS_SIZE / GRID_SIZE;

let currentTool = 'source';
let isRunning = false;
let pollInterval = null;
let gridData = null;
let probes = {};
let sources = [];

const probeColors = [
    '#ff6b6b', '#4ecdc4', '#ffe66d', '#95e1d3',
    '#f38181', '#aa96da', '#fcbad3', '#a8d8ea'
];

const canvas = document.getElementById('heatCanvas');
const ctx = canvas.getContext('2d');
const chartCanvas = document.getElementById('chartCanvas');
const chartCtx = chartCanvas.getContext('2d');

const statusText = document.getElementById('statusText');
const progressBar = document.getElementById('progressBar');
const progressText = document.getElementById('progressText');
const simTimeEl = document.getElementById('simTime');
const totalTimeEl = document.getElementById('totalTime');
const stepCountEl = document.getElementById('stepCount');
const etaTimeEl = document.getElementById('etaTime');
const maxTempEl = document.getElementById('maxTemp');
const dtValueEl = document.getElementById('dtValue');
const cursorInfo = document.getElementById('cursorInfo');

const btnStart = document.getElementById('btnStart');
const btnPause = document.getElementById('btnPause');
const btnReset = document.getElementById('btnReset');
const btnClearSources = document.getElementById('btnClearSources');
const btnClearProbes = document.getElementById('btnClearProbes');

const toolButtons = document.querySelectorAll('.btn-tool');
const sourceTempInput = document.getElementById('sourceTemp');
const sourceRadiusInput = document.getElementById('sourceRadius');

const probeListEl = document.getElementById('probeList');
const chartLegendEl = document.getElementById('chartLegend');

function init() {
    setupEventListeners();
    fetchState();
    startPolling();
}

function setupEventListeners() {
    toolButtons.forEach(btn => {
        btn.addEventListener('click', () => {
            toolButtons.forEach(b => b.classList.remove('active'));
            btn.classList.add('active');
            currentTool = btn.dataset.tool;
        });
    });

    canvas.addEventListener('click', handleCanvasClick);
    canvas.addEventListener('mousemove', handleCanvasMove);
    canvas.addEventListener('mouseleave', () => {
        cursorInfo.textContent = '坐标: --';
    });

    btnStart.addEventListener('click', handleStart);
    btnPause.addEventListener('click', handlePause);
    btnReset.addEventListener('click', handleReset);
    btnClearSources.addEventListener('click', handleClearSources);
    btnClearProbes.addEventListener('click', handleClearProbes);
}

function handleCanvasClick(e) {
    const rect = canvas.getBoundingClientRect();
    const x = Math.floor((e.clientX - rect.left) / CELL_SIZE);
    const y = Math.floor(GRID_SIZE - 1 - (e.clientY - rect.top) / CELL_SIZE);

    if (x < 0 || x >= GRID_SIZE || y < 0 || y >= GRID_SIZE) return;

    if (currentTool === 'source') {
        addSource(x, y);
    } else if (currentTool === 'probe') {
        addProbe(x, y);
    }
}

function handleCanvasMove(e) {
    const rect = canvas.getBoundingClientRect();
    const x = Math.floor((e.clientX - rect.left) / CELL_SIZE);
    const y = Math.floor(GRID_SIZE - 1 - (e.clientY - rect.top) / CELL_SIZE);

    if (x >= 0 && x < GRID_SIZE && y >= 0 && y < GRID_SIZE) {
        let temp = '--';
        if (gridData && gridData[y] && gridData[y][x] !== undefined) {
            temp = gridData[y][x].toFixed(1);
        }
        cursorInfo.textContent = `坐标: (${x}, ${y})  温度: ${temp}°C`;
    } else {
        cursorInfo.textContent = '坐标: --';
    }
}

async function handleStart() {
    try {
        const res = await fetch('/api/start', { method: 'POST' });
        const state = await res.json();
        updateState(state);
    } catch (e) {
        console.error('Start error:', e);
    }
}

async function handlePause() {
    try {
        const res = await fetch('/api/pause', { method: 'POST' });
        const state = await res.json();
        updateState(state);
    } catch (e) {
        console.error('Pause error:', e);
    }
}

async function handleReset() {
    try {
        const res = await fetch('/api/reset', { method: 'POST' });
        const state = await res.json();
        updateState(state);
    } catch (e) {
        console.error('Reset error:', e);
    }
}

async function handleClearSources() {
    try {
        const res = await fetch('/api/sources', { method: 'DELETE' });
        const data = await res.json();
        sources = data.sources || [];
        updateState(data.state);
    } catch (e) {
        console.error('Clear sources error:', e);
    }
}

async function handleClearProbes() {
    try {
        const res = await fetch('/api/probes', { method: 'DELETE' });
        probes = {};
        updateProbeList();
        drawChart();
    } catch (e) {
        console.error('Clear probes error:', e);
    }
}

async function addSource(x, y) {
    const temperature = parseFloat(sourceTempInput.value) || 100;
    const radius = parseInt(sourceRadiusInput.value) || 3;

    try {
        const res = await fetch('/api/source', {
            method: 'POST',
            headers: { 'Content-Type': 'application/json' },
            body: JSON.stringify({ x, y, temperature, radius })
        });
        const data = await res.json();
        sources = data.state.sources || [];
        updateState(data.state);
    } catch (e) {
        console.error('Add source error:', e);
    }
}

async function addProbe(x, y) {
    try {
        const res = await fetch('/api/probe', {
            method: 'POST',
            headers: { 'Content-Type': 'application/json' },
            body: JSON.stringify({ x, y })
        });
        const data = await res.json();
        if (data.probe) {
            probes[data.probe.id] = data.probe;
            updateProbeList();
            drawChart();
        }
    } catch (e) {
        console.error('Add probe error:', e);
    }
}

async function removeProbe(probeId) {
    try {
        await fetch(`/api/probe/${probeId}`, { method: 'DELETE' });
        delete probes[probeId];
        updateProbeList();
        drawChart();
    } catch (e) {
        console.error('Remove probe error:', e);
    }
}

async function fetchState() {
    try {
        const res = await fetch('/api/state');
        const state = await res.json();
        updateState(state);
    } catch (e) {
        console.error('Fetch state error:', e);
    }
}

function startPolling() {
    if (pollInterval) clearInterval(pollInterval);
    pollInterval = setInterval(() => {
        fetchState();
    }, 500);
}

function updateState(state) {
    const status = state.status;
    isRunning = (status === 'running');

    const statusMap = {
        'idle': '空闲',
        'running': '运行中',
        'paused': '已暂停',
        'completed': '已完成',
        'stopped': '已停止',
        'error': '错误'
    };
    statusText.textContent = statusMap[status] || status;
    statusText.className = `status-${status}`;

    const progress = Math.min(state.progress || 0, 100);
    progressBar.style.width = progress + '%';
    progressText.textContent = progress.toFixed(1) + '%';

    simTimeEl.textContent = state.sim_time?.toFixed(2) || '0.00';
    totalTimeEl.textContent = state.total_time?.toFixed(1) || '50.0';
    stepCountEl.textContent = state.step || 0;
    etaTimeEl.textContent = (state.eta > 0 ? state.eta.toFixed(1) : '--');
    maxTempEl.textContent = state.max_temp?.toFixed(2) || '--';
    dtValueEl.textContent = state.dt?.toFixed(4) || '--';

    if (state.grid) {
        gridData = state.grid;
        renderGrid();
    }

    if (state.sources) {
        sources = state.sources;
    }

    if (state.probes) {
        for (const [id, probe] of Object.entries(state.probes)) {
            if (probes[id]) {
                probes[id] = probe;
            }
        }
        updateProbeList();
        drawChart();
    }

    updateButtons(status);
}

function updateButtons(status) {
    if (status === 'running') {
        btnStart.disabled = true;
        btnPause.disabled = false;
        btnPause.textContent = '⏸ 暂停';
    } else if (status === 'paused') {
        btnStart.disabled = false;
        btnStart.textContent = '▶ 继续';
        btnPause.disabled = true;
    } else if (status === 'completed') {
        btnStart.disabled = true;
        btnPause.disabled = true;
    } else {
        btnStart.disabled = false;
        btnStart.textContent = '▶ 开始';
        btnPause.disabled = true;
    }
}

function renderGrid() {
    if (!gridData) return;

    const imageData = ctx.createImageData(CANVAS_SIZE, CANVAS_SIZE);
    const data = imageData.data;

    for (let py = 0; py < CANVAS_SIZE; py++) {
        const gridY = GRID_SIZE - 1 - Math.floor(py / CELL_SIZE);
        for (let px = 0; px < CANVAS_SIZE; px++) {
            const gridX = Math.floor(px / CELL_SIZE);

            const temp = gridData[gridY]?.[gridX] || 0;
            const [r, g, b] = tempToColor(temp);

            const idx = (py * CANVAS_SIZE + px) * 4;
            data[idx] = r;
            data[idx + 1] = g;
            data[idx + 2] = b;
            data[idx + 3] = 255;
        }
    }

    ctx.putImageData(imageData, 0, 0);
    drawSources();
    drawProbes();
}

function tempToColor(temp) {
    const t = Math.max(0, Math.min(1, temp / 100));

    const colors = [
        [0, 0, 51],
        [0, 0, 128],
        [0, 0, 255],
        [0, 128, 255],
        [0, 255, 255],
        [128, 255, 128],
        [255, 255, 0],
        [255, 128, 0],
        [255, 0, 0],
        [128, 0, 0]
    ];

    const scaled = t * (colors.length - 1);
    const idx = Math.floor(scaled);
    const frac = scaled - idx;

    if (idx >= colors.length - 1) return colors[colors.length - 1];
    if (idx < 0) return colors[0];

    const c1 = colors[idx];
    const c2 = colors[idx + 1];

    return [
        Math.round(c1[0] + (c2[0] - c1[0]) * frac),
        Math.round(c1[1] + (c2[1] - c1[1]) * frac),
        Math.round(c1[2] + (c2[2] - c1[2]) * frac)
    ];
}

function drawSources() {
    sources.forEach(src => {
        const cx = src.x * CELL_SIZE + CELL_SIZE / 2;
        const cy = (GRID_SIZE - 1 - src.y) * CELL_SIZE + CELL_SIZE / 2;
        const radius = src.radius * CELL_SIZE;

        ctx.beginPath();
        ctx.arc(cx, cy, radius, 0, Math.PI * 2);
        ctx.strokeStyle = 'rgba(255, 255, 255, 0.8)';
        ctx.lineWidth = 2;
        ctx.stroke();

        ctx.fillStyle = 'white';
        ctx.font = 'bold 11px Arial';
        ctx.textAlign = 'center';
        ctx.fillText(`${src.temperature}°C`, cx, cy + 4);
    });
}

function drawProbes() {
    let colorIdx = 0;
    for (const probe of Object.values(probes)) {
        const color = probeColors[colorIdx % probeColors.length];
        colorIdx++;

        const cx = probe.x * CELL_SIZE + CELL_SIZE / 2;
        const cy = (GRID_SIZE - 1 - probe.y) * CELL_SIZE + CELL_SIZE / 2;

        ctx.beginPath();
        ctx.arc(cx, cy, 6, 0, Math.PI * 2);
        ctx.fillStyle = color;
        ctx.fill();
        ctx.strokeStyle = 'white';
        ctx.lineWidth = 2;
        ctx.stroke();

        ctx.fillStyle = 'white';
        ctx.font = 'bold 10px Arial';
        ctx.textAlign = 'center';
        const label = 'P' + probe.id.split('_')[1];
        ctx.fillText(label, cx, cy - 10);
    }
}

function updateProbeList() {
    const probeArr = Object.values(probes);
    if (probeArr.length === 0) {
        probeListEl.innerHTML = '<p class="empty-hint">点击画布添加探针...</p>';
        return;
    }

    probeListEl.innerHTML = '';
    let colorIdx = 0;

    for (const [id, probe] of Object.entries(probes)) {
        const color = probeColors[colorIdx % probeColors.length];
        colorIdx++;

        const latestTemp = probe.temperatures?.length
            ? probe.temperatures[probe.temperatures.length - 1].toFixed(2)
            : '--';

        const item = document.createElement('div');
        item.className = 'probe-item';
        item.innerHTML = `
            <div class="probe-info">
                <div class="probe-color" style="background: ${color}"></div>
                <span>探针${probe.id.split('_')[1]} (${probe.x}, ${probe.y})</span>
            </div>
            <span class="probe-temp">${latestTemp}°C</span>
            <button class="probe-remove" data-id="${id}" title="删除">×</button>
        `;
        probeListEl.appendChild(item);
    }

    probeListEl.querySelectorAll('.probe-remove').forEach(btn => {
        btn.addEventListener('click', (e) => {
            e.stopPropagation();
            removeProbe(btn.dataset.id);
        });
    });
}

function drawChart() {
    const w = chartCanvas.width;
    const h = chartCanvas.height;

    chartCtx.clearRect(0, 0, w, h);

    chartCtx.fillStyle = 'rgba(0, 0, 0, 0.3)';
    chartCtx.fillRect(0, 0, w, h);

    const probeArr = Object.values(probes).filter(p => p.times && p.times.length > 0);
    if (probeArr.length === 0) {
        chartCtx.fillStyle = '#666';
        chartCtx.font = '12px Arial';
        chartCtx.textAlign = 'center';
        chartCtx.fillText('添加探针后显示温度曲线', w / 2, h / 2);
        chartLegendEl.innerHTML = '';
        return;
    }

    const padding = { top: 10, right: 10, bottom: 25, left: 45 };
    const chartW = w - padding.left - padding.right;
    const chartH = h - padding.top - padding.bottom;

    let maxTime = 50;
    let maxTemp = 100;
    let minTemp = 0;

    for (const p of probeArr) {
        if (p.times.length > 0) {
            maxTime = Math.max(maxTime, p.times[p.times.length - 1]);
        }
        if (p.temperatures.length > 0) {
            maxTemp = Math.max(maxTemp, ...p.temperatures);
            minTemp = Math.min(minTemp, ...p.temperatures);
        }
    }

    const tempRange = maxTemp - minTemp || 1;
    maxTemp += tempRange * 0.1;
    minTemp -= tempRange * 0.05;

    chartCtx.strokeStyle = 'rgba(255, 255, 255, 0.1)';
    chartCtx.lineWidth = 1;

    for (let i = 0; i <= 4; i++) {
        const y = padding.top + (chartH * i / 4);
        chartCtx.beginPath();
        chartCtx.moveTo(padding.left, y);
        chartCtx.lineTo(w - padding.right, y);
        chartCtx.stroke();

        const tempVal = maxTemp - (maxTemp - minTemp) * i / 4;
        chartCtx.fillStyle = '#888';
        chartCtx.font = '10px Arial';
        chartCtx.textAlign = 'right';
        chartCtx.fillText(tempVal.toFixed(0), padding.left - 5, y + 3);
    }

    chartCtx.fillStyle = '#888';
    chartCtx.textAlign = 'center';
    chartCtx.font = '10px Arial';
    for (let i = 0; i <= 4; i++) {
        const timeVal = maxTime * i / 4;
        const x = padding.left + chartW * i / 4;
        chartCtx.fillText(timeVal.toFixed(0) + 's', x, h - 8);
    }

    let colorIdx = 0;
    chartLegendEl.innerHTML = '';

    for (const probe of probeArr) {
        const color = probeColors[colorIdx % probeColors.length];
        colorIdx++;

        chartCtx.strokeStyle = color;
        chartCtx.lineWidth = 2;
        chartCtx.beginPath();

        for (let i = 0; i < probe.times.length; i++) {
            const x = padding.left + (probe.times[i] / maxTime) * chartW;
            const y = padding.top + (1 - (probe.temperatures[i] - minTemp) / (maxTemp - minTemp)) * chartH;

            if (i === 0) {
                chartCtx.moveTo(x, y);
            } else {
                chartCtx.lineTo(x, y);
            }
        }
        chartCtx.stroke();

        const legendItem = document.createElement('div');
        legendItem.className = 'legend-item';
        legendItem.innerHTML = `
            <div class="legend-dot" style="background: ${color}"></div>
            <span>探针${probe.id.split('_')[1]}</span>
        `;
        chartLegendEl.appendChild(legendItem);
    }
}

init();
