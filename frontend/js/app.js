/* ═══════════════════════════════════════════════════════════════
   SmartView OPC – Frontend Logik
   SSE (Server-Sent Events) statt Polling, Alarme, Historie, Steuerung
   ═══════════════════════════════════════════════════════════════ */

// Speichert ob die Anlage gerade läuft (für Start-Button Farbe)
let startActive = false;

// ─── Verbindungsstatus anzeigen ───────────────────────────────────────────────
function setOnlineStatus(online) {
  // statusDot = farbiger Kreis in der Navbar, statusText = Text daneben
  const dot  = document.getElementById("statusDot");
  const text = document.getElementById("statusText");
  dot.className = "status-dot " + (online ? "online" : "offline");  // CSS-Klasse wechseln
  text.textContent = online ? "OPC verbunden" : "Keine Verbindung";
  text.style.color = online ? "#10b981" : "#ef4444";  // Grün oder Rot
}

// ─── Wert formatieren ─────────────────────────────────────────────────────────
function fmt(v) {
  // null/undefined → Strich, Zahlen auf 2 Nachkommastellen, Rest als String
  if (v === null || v === undefined) return "—";
  if (typeof v === "number") return v.toFixed(2);
  return String(v);
}

// ─── Digitalen Indikator (Förderband, Zylinder, Lichtschranke) aktualisieren ─
function updateDigital(ringId, textId, value, textOn, textOff) {
  const ring = document.getElementById(ringId);  // Farbiger Kreis
  const span = document.getElementById(textId);  // Status-Text
  ring.classList.remove("is-on", "is-off");       // Alte CSS-Klasse entfernen

  if (value === null || value === undefined) {
    span.textContent = "Keine Daten";
    span.style.color = "#64748b";  // Grau wenn kein Wert
    return;
  }

  // true, 1 oder "true" gilt als eingeschaltet
  const isOn = value === true || value === 1 || String(value).toLowerCase() === "true";
  ring.classList.add(isOn ? "is-on" : "is-off");  // Grün oder Rot
  span.textContent = isOn ? textOn : textOff;
  span.style.color = isOn ? "#10b981" : "#ef4444";
}

// ─── Alle Karten im Dashboard aktualisieren ───────────────────────────────────
function updateDashboard(data) {
  if (!data || Object.keys(data).length === 0) return;  // Leere Daten ignorieren

  // Drucksensor (Analog): Zahl anzeigen + Balken proportional füllen
  const druck = data.druck;
  document.getElementById("valDruck").textContent = fmt(druck);
  const bar = document.getElementById("druckBar");
  if (typeof druck === "number") {
    // Balkenbreite: 0–10 bar → 0–100%
    bar.style.width = Math.max(0, Math.min(100, (druck / 10) * 100)) + "%";
    bar.classList.toggle("warning", druck > 7);  // Gelbe Farbe ab 7 bar
  } else {
    bar.style.width = "0%";
  }

  // Digitale Werte: Karte + Statustext aktualisieren
  updateDigital("ringFoerderband", "valFoerderband", data.foerderband_ein, "Läuft", "Gestoppt");
  updateDigital("ringZylinder", "valZylinder", data.zylinder_ausgefahren, "Ausgefahren", "Eingefahren");

  // Lichtschranke ist invertiert: false = unterbrochen = Bauteil vorhanden
  // Deshalb wird der Wert mit ! negiert bevor er angezeigt wird
  updateDigital("ringLichtschranke", "valLichtschranke", !data.sensor_lichtschranke, "Bauteil vorhanden", "Frei");

  // Zeitstempel des letzten Updates und Rohdaten-JSON aktualisieren
  document.getElementById("lastUpdate").textContent = new Date().toLocaleTimeString("de-DE");
  document.getElementById("rawJson").textContent = JSON.stringify(data, null, 2);
}

// ─── Alarm-Banner anzeigen oder verstecken ────────────────────────────────────
function updateAlarms(alarms) {
  const banner = document.getElementById("alarmBanner");
  const list   = document.getElementById("alarmList");
  if (!alarms || alarms.length === 0) {
    banner.style.display = "none";  // Kein Alarm → Banner ausblenden
    return;
  }
  // Banner einblenden und Alarme als HTML-Elemente einfügen
  banner.style.display = "block";
  list.innerHTML = alarms.map(a =>
    // CSS-Klasse alarm-warning oder alarm-critical (unterschiedliche Farben)
    `<span class="alarm-item alarm-${a.level}">⚠ ${a.msg}</span>`
  ).join("");
}

// ─── Start-Button Farbe steuern ───────────────────────────────────────────────
function setStartActive(active) {
  startActive = active;
  // CSS-Klasse "active" macht den Button grün wenn Anlage läuft
  document.getElementById("btnStart").classList.toggle("active", active);
}

// ─── Steuerbefehl an Backend senden ──────────────────────────────────────────
async function sendCmd(cmd) {
  const feedback = document.getElementById("cmdFeedback");  // Statuszeile unter den Buttons
  feedback.textContent = "Sende…";
  feedback.style.color = "#94a3b8";

  try {
    // HTTP POST an /api/cmd/<cmd> (z.B. /api/cmd/start)
    const res  = await fetch(`/api/cmd/${cmd}`, { method: "POST" });
    const data = await res.json();

    if (data.ok) {
      // Erfolg: Start-Button grün wenn start, sonst zurücksetzen
      if (cmd === "start") setStartActive(true);
      if (cmd === "stop" || cmd === "reset") setStartActive(false);
      const labels = { start: "Start", stop: "Stop", reset: "Reset" };
      feedback.textContent = `✓ ${labels[cmd]} gesendet`;
      feedback.style.color = "#10b981";  // Grün
    } else {
      feedback.textContent = `✗ ${data.error}`;
      feedback.style.color = "#ef4444";  // Rot
    }
  } catch (err) {
    feedback.textContent = `✗ Fehler: ${err}`;
    feedback.style.color = "#ef4444";
  }
  // Statusmeldung nach 3 Sekunden wieder leeren
  setTimeout(() => { feedback.textContent = ""; }, 3000);
}

// ─── Verlaufstabelle aus der Datenbank laden ──────────────────────────────────
async function loadHistory() {
  const tbody = document.getElementById("historyBody");
  tbody.innerHTML = "<tr><td colspan='5'>Lade…</td></tr>";
  try {
    // GET /api/history?limit=20 → letzte 20 Datenbankeinträge
    const res  = await fetch("/api/history?limit=20");
    const rows = await res.json();
    if (rows.length === 0) {
      tbody.innerHTML = "<tr><td colspan='5'>Keine Daten</td></tr>";
      return;
    }
    // Jede Datenbankzeile als HTML-Tabellenzeile ausgeben
    tbody.innerHTML = rows.map((r, i) => {
      const ts = new Date(r.ts);
      const datum = ts.toLocaleDateString("de-DE");     // z.B. "23.03.2026"
      const uhrzeit = ts.toLocaleTimeString("de-DE");   // z.B. "14:05:12"
      return `<tr${i === 0 ? ' class="row-latest"' : ""}> <!-- Neueste Zeile hervorheben -->
        <td><span class="ts-date">${datum}</span> <span class="ts-time">${uhrzeit}</span></td>
        <td>${r.druck !== null ? r.druck.toFixed(2) + " bar" : "—"}</td>
        <td class="${r.foerderband_ein ? "td-on" : "td-off"}">${r.foerderband_ein ? "Läuft" : "Gestoppt"}</td>
        <td class="${r.zylinder_ausgefahren ? "td-on" : "td-off"}">${r.zylinder_ausgefahren ? "Ausgefahren" : "Eingefahren"}</td>
        <!-- Lichtschranke wieder invertiert: 0 in DB = unterbrochen = Bauteil vorhanden -->
        <td class="${!r.sensor_lichtschranke ? "td-on" : "td-off"}">${!r.sensor_lichtschranke ? "Vorhanden" : "Frei"}</td>
      </tr>`;
    }).join("");
  } catch {
    tbody.innerHTML = "<tr><td colspan='5'>Fehler beim Laden</td></tr>";
  }
}

// ─── Rohdaten-Konsole ein-/ausklappen ─────────────────────────────────────────
function toggleRaw() {
  const body   = document.getElementById("rawBody");
  const toggle = document.getElementById("rawToggle");
  body.classList.toggle("hidden");  // CSS-Klasse hidden ein/ausschalten
  toggle.textContent = body.classList.contains("hidden") ? "▼" : "▲";
}

// ─── Verlaufstabelle ein-/ausklappen ──────────────────────────────────────────
function toggleHistory() {
  const body   = document.getElementById("historyBody").closest(".raw-section");
  const inner  = document.getElementById("historyInner");
  const toggle = document.getElementById("historyToggle");
  const hidden = inner.classList.toggle("hidden");
  toggle.textContent = hidden ? "▼" : "▲";
  if (!hidden) loadHistory();  // Daten nur laden wenn Tabelle aufgeklappt wird
}

// ─── SSE-Verbindung zum Server aufbauen ───────────────────────────────────────
function startSSE() {
  // EventSource öffnet eine dauerhafte HTTP-Verbindung zu /api/stream
  // Der Browser reconnectet automatisch wenn die Verbindung abbricht (nach ~3s)
  const source = new EventSource("/api/stream");

  // Wird bei jeder Nachricht vom Server aufgerufen
  source.onmessage = (event) => {
    const payload = JSON.parse(event.data);  // JSON-String zu Objekt parsen
    setOnlineStatus(payload.connected);       // Verbindungsstatus aktualisieren
    updateDashboard(payload.tags);            // Karten aktualisieren
    updateAlarms(payload.alarms);            // Alarm-Banner aktualisieren
  };

  // Wird bei Verbindungsabbruch aufgerufen (Browser versucht automatisch neu)
  source.onerror = () => {
    setOnlineStatus(false);
  };
}

// ─── Start ────────────────────────────────────────────────────────────────────
// SSE-Verbindung sofort beim Laden der Seite starten
startSSE();
