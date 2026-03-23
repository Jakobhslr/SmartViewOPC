/* ═══════════════════════════════════════════════════════════════
   SmartView OPC – Frontend Logik
   SSE (Server-Sent Events) statt Polling, Alarme, Historie
   ═══════════════════════════════════════════════════════════════ */

let startActive = false;

// ─── Status Badge ─────────────────────────────────────────────
function setOnlineStatus(online) {
  const dot  = document.getElementById("statusDot");
  const text = document.getElementById("statusText");
  dot.className = "status-dot " + (online ? "online" : "offline");
  text.textContent = online ? "OPC verbunden" : "Keine Verbindung";
  text.style.color = online ? "#10b981" : "#ef4444";
}

// ─── Formatierung ─────────────────────────────────────────────
function fmt(v) {
  if (v === null || v === undefined) return "—";
  if (typeof v === "number") return v.toFixed(2);
  return String(v);
}

// ─── Digital-Indikator ────────────────────────────────────────
function updateDigital(ringId, textId, value, textOn, textOff) {
  const ring = document.getElementById(ringId);
  const span = document.getElementById(textId);
  ring.classList.remove("is-on", "is-off");

  if (value === null || value === undefined) {
    span.textContent = "Keine Daten";
    span.style.color = "#64748b";
    return;
  }

  const isOn = value === true || value === 1 || String(value).toLowerCase() === "true";
  ring.classList.add(isOn ? "is-on" : "is-off");
  span.textContent = isOn ? textOn : textOff;
  span.style.color = isOn ? "#10b981" : "#ef4444";
}

// ─── Dashboard aktualisieren ──────────────────────────────────
function updateDashboard(data) {
  if (!data || Object.keys(data).length === 0) return;

  // Drucksensor (Analog)
  const druck = data.druck;
  document.getElementById("valDruck").textContent = fmt(druck);
  const bar = document.getElementById("druckBar");
  if (typeof druck === "number") {
    bar.style.width = Math.max(0, Math.min(100, (druck / 10) * 100)) + "%";
    bar.classList.toggle("warning", druck > 7);
  } else {
    bar.style.width = "0%";
  }

  // Förderband
  updateDigital("ringFoerderband", "valFoerderband", data.foerderband_ein, "Läuft", "Gestoppt");

  // Zylinder
  updateDigital("ringZylinder", "valZylinder", data.zylinder_ausgefahren, "Ausgefahren", "Eingefahren");

  // Lichtschranke (invertiert: false = unterbrochen = Bauteil vorhanden)
  updateDigital("ringLichtschranke", "valLichtschranke", !data.sensor_lichtschranke, "Bauteil vorhanden", "Frei");

  // Letztes Update & Rohdaten
  document.getElementById("lastUpdate").textContent = new Date().toLocaleTimeString("de-DE");
  document.getElementById("rawJson").textContent = JSON.stringify(data, null, 2);
}

// ─── Alarme anzeigen ──────────────────────────────────────────
function updateAlarms(alarms) {
  const banner = document.getElementById("alarmBanner");
  const list   = document.getElementById("alarmList");
  if (!alarms || alarms.length === 0) {
    banner.style.display = "none";
    return;
  }
  banner.style.display = "block";
  list.innerHTML = alarms.map(a =>
    `<span class="alarm-item alarm-${a.level}">⚠ ${a.msg}</span>`
  ).join("");
}

// ─── Start-Button Zustand ─────────────────────────────────────
function setStartActive(active) {
  startActive = active;
  document.getElementById("btnStart").classList.toggle("active", active);
}

// ─── Steuerbefehl senden ──────────────────────────────────────
async function sendCmd(cmd) {
  const feedback = document.getElementById("cmdFeedback");
  feedback.textContent = "Sende…";
  feedback.style.color = "#94a3b8";

  try {
    const res  = await fetch(`/api/cmd/${cmd}`, { method: "POST" });
    const data = await res.json();

    if (data.ok) {
      if (cmd === "start") setStartActive(true);
      if (cmd === "stop" || cmd === "reset") setStartActive(false);
      const labels = { start: "Start", stop: "Stop", reset: "Reset" };
      feedback.textContent = `✓ ${labels[cmd]} gesendet`;
      feedback.style.color = "#10b981";
    } else {
      feedback.textContent = `✗ ${data.error}`;
      feedback.style.color = "#ef4444";
    }
  } catch (err) {
    feedback.textContent = `✗ Fehler: ${err}`;
    feedback.style.color = "#ef4444";
  }
  setTimeout(() => { feedback.textContent = ""; }, 3000);
}

// ─── Historie laden und anzeigen ──────────────────────────────
async function loadHistory() {
  const tbody = document.getElementById("historyBody");
  tbody.innerHTML = "<tr><td colspan='5'>Lade…</td></tr>";
  try {
    const res  = await fetch("/api/history?limit=20");
    const rows = await res.json();
    if (rows.length === 0) {
      tbody.innerHTML = "<tr><td colspan='5'>Keine Daten</td></tr>";
      return;
    }
    tbody.innerHTML = rows.map(r => `
      <tr>
        <td>${r.ts}</td>
        <td>${r.druck !== null ? r.druck.toFixed(2) + " bar" : "—"}</td>
        <td class="${r.foerderband_ein ? "td-on" : "td-off"}">${r.foerderband_ein ? "Läuft" : "Gestoppt"}</td>
        <td class="${r.zylinder_ausgefahren ? "td-on" : "td-off"}">${r.zylinder_ausgefahren ? "Ausgefahren" : "Eingefahren"}</td>
        <td class="${!r.sensor_lichtschranke ? "td-on" : "td-off"}">${!r.sensor_lichtschranke ? "Vorhanden" : "Frei"}</td>
      </tr>`).join("");
  } catch {
    tbody.innerHTML = "<tr><td colspan='5'>Fehler beim Laden</td></tr>";
  }
}

// ─── Rohdaten Toggle ──────────────────────────────────────────
function toggleRaw() {
  const body   = document.getElementById("rawBody");
  const toggle = document.getElementById("rawToggle");
  body.classList.toggle("hidden");
  toggle.textContent = body.classList.contains("hidden") ? "▼" : "▲";
}

// ─── Historie Toggle ──────────────────────────────────────────
function toggleHistory() {
  const body   = document.getElementById("historyBody").closest(".raw-section");
  const inner  = document.getElementById("historyInner");
  const toggle = document.getElementById("historyToggle");
  const hidden = inner.classList.toggle("hidden");
  toggle.textContent = hidden ? "▼" : "▲";
  if (!hidden) loadHistory();
}

// ─── SSE Verbindung ───────────────────────────────────────────
function startSSE() {
  const source = new EventSource("/api/stream");

  source.onmessage = (event) => {
    const payload = JSON.parse(event.data);
    setOnlineStatus(payload.connected);
    updateDashboard(payload.tags);
    updateAlarms(payload.alarms);
  };

  source.onerror = () => {
    setOnlineStatus(false);
    // SSE reconnect automatisch durch Browser — nach 3s neuer Versuch
  };
}

// ─── Init ────────────────────────────────────────────────────
startSSE();
