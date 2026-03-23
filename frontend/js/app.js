/* ═══════════════════════════════════════════════════════════════
   SmartView OPC – Frontend Logik
   Polling, Live-Updates, Steuerung
   ═══════════════════════════════════════════════════════════════ */

const API_URL = "/api/tags";
const POLL_MS = 1000;

// Merkt ob Start aktiv ist (für Button-Farbe)
let startActive = false;

// ─── Status Badge ────────────────────────────────────────────
function setOnlineStatus(online) {
  const dot  = document.getElementById("statusDot");
  const text = document.getElementById("statusText");
  dot.className = "status-dot " + (online ? "online" : "offline");
  text.textContent = online ? "OPC verbunden" : "Keine Verbindung";
  text.style.color = online ? "#10b981" : "#ef4444";
}

// ─── Formatierung ────────────────────────────────────────────
function fmt(v) {
  if (v === null || v === undefined) return "—";
  if (typeof v === "number") return v.toFixed(2);
  return String(v);
}

// ─── Digital-Indikator aktualisieren ─────────────────────────
function updateDigital(ringId, textId, value, textOn, textOff) {
  const ring = document.getElementById(ringId);
  const span = document.getElementById(textId);
  ring.classList.remove("is-on", "is-off");

  if (value === null || value === undefined) {
    span.textContent = "Keine Daten";
    span.style.color = "#64748b";
    return;
  }

  const isOn = (value === true) || (value === 1) || (String(value).toLowerCase() === "true");
  ring.classList.add(isOn ? "is-on" : "is-off");
  span.textContent = isOn ? textOn : textOff;
  span.style.color = isOn ? "#10b981" : "#ef4444";
}

// ─── Start-Button-Zustand setzen ─────────────────────────────
function setStartActive(active) {
  startActive = active;
  document.getElementById("btnStart").classList.toggle("active", active);
}

// ─── Steuerbefehl senden ─────────────────────────────────────
async function sendCmd(cmd) {
  const feedback = document.getElementById("cmdFeedback");
  feedback.textContent = "Sende…";
  feedback.style.color = "#94a3b8";

  try {
    const res = await fetch(`/api/cmd/${cmd}`, {
      method: "POST",
      headers: { "Content-Type": "application/json" },
      body: JSON.stringify({ value: true }),
    });
    const data = await res.json();

    if (data.ok) {
      // Button-Zustand aktualisieren
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

// ─── Polling ─────────────────────────────────────────────────
async function poll() {
  try {
    const res = await fetch(API_URL, {
      cache: "no-store",
      headers: { "Accept": "application/json" },
    });
    if (!res.ok) throw new Error("HTTP " + res.status);

    const data = await res.json();
    setOnlineStatus(true);

    // Drucksensor (Analog)
    const druck = data.druck;
    document.getElementById("valDruck").textContent = fmt(druck);

    const bar = document.getElementById("druckBar");
    if (typeof druck === "number") {
      const pct = Math.max(0, Math.min(100, (druck / 10) * 100));
      bar.style.width = pct + "%";
      bar.classList.toggle("warning", druck > 7);
    } else {
      bar.style.width = "0%";
    }

    // Förderband (Digital)
    updateDigital("ringFoerderband", "valFoerderband", data.foerderband_ein, "Läuft", "Gestoppt");

    // Zylinder (Digital)
    updateDigital("ringZylinder", "valZylinder", data.zylinder_ausgefahren, "Ausgefahren", "Eingefahren");

    // Lichtschranke (Digital) — unterbrochen = Bauteil vorhanden
    // Lichtschranke: false = unterbrochen = Bauteil vorhanden
    updateDigital("ringLichtschranke", "valLichtschranke", !data.sensor_lichtschranke, "Bauteil vorhanden", "Frei");

    // Letztes Update
    document.getElementById("lastUpdate").textContent = new Date().toLocaleTimeString("de-DE");

    // Rohdaten
    document.getElementById("rawJson").textContent = JSON.stringify(data, null, 2);

  } catch (err) {
    setOnlineStatus(false);
    document.getElementById("rawJson").textContent = JSON.stringify({ error: String(err) }, null, 2);
  }
}

// ─── Rohdaten Toggle ─────────────────────────────────────────
function toggleRaw() {
  const body   = document.getElementById("rawBody");
  const toggle = document.getElementById("rawToggle");
  body.classList.toggle("hidden");
  toggle.textContent = body.classList.contains("hidden") ? "▼" : "▲";
}

// ─── Init ────────────────────────────────────────────────────
poll();
setInterval(poll, POLL_MS);
