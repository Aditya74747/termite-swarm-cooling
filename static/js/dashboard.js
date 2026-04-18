/* dashboard.js — polls /api/state every 600ms and renders */

let paused = false;
let selectedRack = null;

// ── Colour helpers ────────────────────────────────────────────────────
function tempColor(t) {
  if (t < 24) return { bg: '#0f1e3a', border: '#1e3a6e', text: '#60a5fa' };
  if (t < 27) return { bg: '#0d2218', border: '#14532d', text: '#4ade80' };
  if (t < 32) return { bg: '#271a06', border: '#78350f', text: '#fbbf24' };
  if (t < 40) return { bg: '#2a0f0f', border: '#7f1d1d', text: '#f87171' };
  return { bg: '#3b0000', border: '#991b1b', text: '#fca5a5' };
}

// ── Render rack grid ─────────────────────────────────────────────────
function renderGrid(racks) {
  const grid = document.getElementById('rack-grid');
  racks.forEach((r, i) => {
    let card = document.getElementById(`rack-${i}`);
    if (!card) {
      card = document.createElement('div');
      card.className = 'rack-card';
      card.id = `rack-${i}`;
      card.title = 'Click to inject hotspot';
      card.onclick = () => injectHotspot(i);
      card.innerHTML = `
        <div class="rack-id">R${i + 1}</div>
        <div class="rack-temp" id="rt-${i}">—</div>
        <div class="rack-bars">
          <div class="mini-bar-row">
            <div class="mini-bar-label">SIG</div>
            <div class="mini-bar-track"><div class="mini-bar-fill" id="sig-${i}" style="background:#00c896"></div></div>
          </div>
          <div class="mini-bar-row">
            <div class="mini-bar-label">FAN</div>
            <div class="mini-bar-track"><div class="mini-bar-fill" id="fan-${i}" style="background:#3b82f6"></div></div>
          </div>
        </div>
        <div class="rack-load-text" id="rload-${i}"></div>`;
      grid.appendChild(card);
    }

    const col = tempColor(r.temperature);
    card.style.background = col.bg;
    card.style.borderColor = col.border;
    card.classList.toggle('hot', r.temperature > 35);

    document.getElementById(`rt-${i}`).style.color = col.text;
    document.getElementById(`rt-${i}`).textContent = r.temperature.toFixed(1) + '°';
    document.getElementById(`sig-${i}`).style.width = Math.min(100, r.heat_signal / 1.2) + '%';
    document.getElementById(`fan-${i}`).style.width = r.fan_speed + '%';
    document.getElementById(`rload-${i}`).textContent =
      `load ${(r.load * 100).toFixed(0)}%  fan ${r.fan_speed.toFixed(0)}%`;
  });
}

// ── Sparkline ────────────────────────────────────────────────────────
function renderSparkline(history) {
  if (history.length < 2) return;
  const W = 600, H = 52;
  const TARGET_Y = 34; // y pixel for 27°C target line
  const temps = history.map(h => h.avg);
  const minT = Math.min(...temps, 20);
  const maxT = Math.max(...temps, 35);

  function px(t) {
    return H - 4 - ((t - minT) / (maxT - minT + 0.01)) * (H - 10);
  }

  const xs = history.map((_, i) => (i / (history.length - 1)) * W);
  const pts = history.map((h, i) => `${xs[i].toFixed(1)},${px(h.avg).toFixed(1)}`).join(' ');

  const fillPts =
    `${xs[0]},${H} ` + pts + ` ${xs[xs.length - 1]},${H}`;

  document.getElementById('spark-line').setAttribute('points', pts);
  document.getElementById('spark-fill').setAttribute('d',
    `M ${xs[0]} ${H} ` +
    history.map((h, i) => `L ${xs[i].toFixed(1)} ${px(h.avg).toFixed(1)}`).join(' ') +
    ` L ${xs[xs.length - 1]} ${H} Z`
  );
}

// ── Stat cards ───────────────────────────────────────────────────────
function renderStats(s) {
  const avg = document.getElementById('s-avg');
  avg.textContent = s.avg_temp.toFixed(1) + '°';
  avg.className = 'stat-val ' + (s.avg_temp < 27 ? 'ok' : s.avg_temp < 32 ? 'warn' : 'danger');

  const max = document.getElementById('s-max');
  max.textContent = s.max_temp.toFixed(1) + '°';
  max.className = 'stat-val ' + (s.max_temp < 27 ? 'ok' : s.max_temp < 35 ? 'warn' : 'danger');

  const hot = document.getElementById('s-hot');
  hot.textContent = s.hot_zones;
  hot.className = 'stat-val ' + (s.hot_zones === 0 ? 'ok' : s.hot_zones < 3 ? 'warn' : 'danger');

  document.getElementById('s-fan').textContent = s.avg_fan.toFixed(0) + '%';
}

// ── Event log ────────────────────────────────────────────────────────
let lastLogCount = 0;
function renderLog(entries) {
  if (entries.length === lastLogCount) return;
  lastLogCount = entries.length;
  const el = document.getElementById('event-log');
  el.innerHTML = entries.slice().reverse().map(e => {
    const isCrit = e.msg.includes('CRITICAL') || e.msg.includes('above 35');
    const isWarn = e.msg.includes('WARNING') || e.msg.includes('Hotspot') || e.msg.includes('spike');
    return `<div class="log-entry ${isCrit ? 'crit' : isWarn ? 'warn' : ''}">
      <span class="log-tick">t${e.t}</span> ${e.msg}
    </div>`;
  }).join('');
}

// ── Header ───────────────────────────────────────────────────────────
function renderHeader(s) {
  document.getElementById('h-tick').textContent = s.tick;
  document.getElementById('h-elapsed').textContent = s.elapsed + 's';
  document.getElementById('h-ambient').textContent = s.ambient + '°C';
}

// ── Poll loop ────────────────────────────────────────────────────────
async function poll() {
  try {
    const res = await fetch('/api/state');
    const s = await res.json();
    renderGrid(s.racks);
    renderStats(s);
    renderSparkline(s.history);
    renderLog(s.event_log);
    renderHeader(s);
  } catch (e) {
    console.warn('Poll error:', e);
  }
}

setInterval(poll, 600);
poll();

// ── Control actions ──────────────────────────────────────────────────
async function post(action, extra = {}) {
  await fetch('/api/control', {
    method: 'POST',
    headers: { 'Content-Type': 'application/json' },
    body: JSON.stringify({ action, ...extra }),
  });
}

function addHotspot() {
  const idx = Math.floor(Math.random() * 24);
  post('add_hotspot', { rack_index: idx });
}

function injectHotspot(idx) {
  post('add_hotspot', { rack_index: idx });
}

function loadSpike() { post('add_random_load_spike'); }

function resetSim() { post('reset'); }

function setAmbient(v) {
  document.getElementById('lbl-ambient').textContent = v + '°C';
  post('set_ambient', { value: v });
}

function setEvap(v) {
  document.getElementById('lbl-evap').textContent = v;
  post('set_evaporation', { value: v });
}

function togglePause() {
  paused = !paused;
  const btn = document.getElementById('btn-pause');
  const dot = document.getElementById('status-dot');
  if (paused) {
    btn.innerHTML = '<span class="btn-icon">▶</span> Resume simulation';
    dot.classList.add('paused');
  } else {
    btn.innerHTML = '<span class="btn-icon">⏸</span> Pause simulation';
    dot.classList.remove('paused');
  }
  post('toggle_pause');
}
