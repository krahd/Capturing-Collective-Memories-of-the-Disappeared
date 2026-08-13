const state = {
  session: null,
  config: { llm_configured: false },
  voicePhase: "idle",
  field: null,
  selectedNode: null,
};

const voiceRuntime = {
  recorder: null,
  stream: null,
  context: null,
  analyser: null,
  chunks: [],
  frame: null,
  heardSpeech: false,
  silentSince: 0,
  startedAt: 0,
};

const $ = (id) => document.getElementById(id);

const ACTION_LABELS = {
  sesion_creada: "Sesión iniciada",
  turno_registrado: "Turno preservado",
  anotacion_agregada: "Anotación",
  interpretacion_creada: "Interpretación creada",
  interpretacion_editada: "Edición registrada",
  interpretacion_retirada: "Retiro",
  interpretacion_eliminada: "Eliminación",
  relacion_agregada: "Relación",
  extraccion_ejecutada: "Extracción automática",
  extraccion_fallida: "Extracción fallida",
  entrada_clasificada: "Clasificación de entrada",
  operacion_protocolo: "Operación de protocolo",
  estado_sesion_cambiado: "Estado de la sesión",
  audio_preservado: "Audio preservado",
  transcripcion_asr_creada: "Transcripción ASR",
};

const TYPE_LABELS = {
  conversation: "conversación",
  recollection: "recuerdo",
  person: "persona",
  place: "lugar",
  event: "evento",
  time: "fecha",
  theme: "tema",
};

const MARK_LABELS = {
  uncertainty: "incierto",
  hearsay: "de oídas",
  correction: "corrección",
};

async function api(url, options = {}) {
  const response = await fetch(url, {
    headers: { "Content-Type": "application/json", ...(options.headers || {}) },
    ...options,
  });
  const data = response.headers.get("content-type")?.includes("application/json") ? await response.json() : await response.text();
  if (!response.ok) {
    const message = data?.detail || data?.error || (typeof data === "string" ? data : `HTTP ${response.status}`);
    const error = new Error(message);
    error.payload = data;
    throw error;
  }
  return data;
}

function isRecorded() {
  return Boolean(state.session?.is_recorded);
}

function setSession(session) {
  state.session = session;
  if (session?.id) localStorage.setItem("ccm-current-session", session.id);
  render();
}

function render() {
  renderConversation();
  renderAudit();
  const ready = Boolean(state.session);
  const sessionStatus = state.session?.status || "active";
  const live = ready && !isRecorded() && sessionStatus === "active";
  $("recorded-banner").hidden = !isRecorded();
  $("message").disabled = !live;
  $("message").placeholder = isRecorded()
    ? "Transcripción grabada: no admite turnos nuevos."
    : sessionStatus === "paused"
      ? "La conversación está pausada."
      : sessionStatus !== "active"
        ? "La conversación está detenida."
        : "Escribí acá…";
  $("send").disabled = !live || !state.config.llm_configured;
  $("resume-session").hidden = sessionStatus !== "paused";
  $("voice-toggle").disabled = !live || !state.config.llm_configured || !state.config.voice?.asr_configured || state.voicePhase !== "idle";
  if (state.voicePhase === "idle") renderVoiceAvailability();
  $("export-json").disabled = !ready;
  $("export-md").disabled = !ready;
}

function renderConversation() {
  const root = $("conversation");
  root.innerHTML = "";
  if (!state.session) {
    root.innerHTML = '<p class="muted">Creá una conversación para empezar.</p>';
    return;
  }

  const template = $("turn-template");
  state.session.turns.forEach((turn) => {
    const node = template.content.firstElementChild.cloneNode(true);
    node.classList.add(turn.role);
    node.dataset.turnId = turn.id;
    // A recollection selected in the field lights up in the transcript.
    if (state.selectedNode?.turn_id === turn.id) node.classList.add("lit");

    const meta = node.querySelector(".turn-meta");
    meta.textContent = turn.role === "user" ? "Participante" : "Sistema";
    if (turn.record_kind === "non_testimony/control") {
      node.classList.add("non-testimony");
      const badge = document.createElement("span");
      badge.className = "turn-kind control";
      badge.textContent = `${turn.intent || "control"} · no testimonial`;
      meta.appendChild(badge);
    } else if (turn.input_mode === "voice_asr") {
      const badge = document.createElement("span");
      badge.className = "turn-kind";
      badge.textContent = "voz · transcripción ASR";
      meta.appendChild(badge);
    }

    node.querySelector(".turn-text").textContent = turn.text;
    root.appendChild(node);
  });

  const lit = root.querySelector(".turn.lit");
  if (lit) lit.scrollIntoView({ behavior: "smooth", block: "center" });
  else root.scrollTop = root.scrollHeight;
}

/* ------------------------------------------------------------------ *
 * The memory field.
 *
 * Nothing here is a curation control. The graph is a by-product of
 * conversations having happened, and it is drawn across all of them, so the
 * visible proposition is accumulation rather than annotation.
 * ------------------------------------------------------------------ */

const sim = { nodes: [], edges: [], byId: new Map(), alpha: 0, frame: null };

const NODE_RADIUS = { conversation: 8.5, recollection: 5 };

function radiusFor(node) {
  if (NODE_RADIUS[node.type]) return NODE_RADIUS[node.type];
  // Entities carried by several conversations are drawn larger. That growth is
  // the collective structure becoming visible.
  const reach = Math.max(1, (node.conversations || []).length);
  return 3.6 + 2.4 * Math.sqrt(reach - 1);
}

async function loadField() {
  try {
    const field = await api(`/api/memory-field?focus=${state.session?.id || ""}`);
    state.field = field;
    syncSimulation(field);
    renderCounters(field);
    renderChips(field);
    kick();
  } catch (error) {
    console.error("memory field", error);
  }
}

function syncSimulation(field) {
  const svg = $("field-graph");
  const width = svg.clientWidth || 460;
  const height = svg.clientHeight || 460;
  const next = [];
  const byId = new Map();

  const firstLoad = sim.nodes.length === 0;
  field.nodes.forEach((raw, index) => {
    const existing = sim.byId.get(raw.id);
    let node;
    if (existing) {
      node = Object.assign(existing, raw);
    } else if (firstLoad) {
      // Seed an existing corpus spread out. Starting everything at one point
      // makes the repulsion term explode and flings the graph into the walls;
      // seeding on a ring leaves a permanent hole in the middle. Uniform over
      // the area avoids both.
      const angle = Math.random() * Math.PI * 2;
      const spread = Math.sqrt(Math.random()) * Math.min(width, height) * 0.46;
      node = {
        ...raw,
        x: width / 2 + Math.cos(angle) * spread,
        y: height / 2 + Math.sin(angle) * spread,
        vx: 0,
        vy: 0,
        born: performance.now() - 900,
      };
    } else {
      // Something new said just now: it arrives near the middle and settles
      // outward, so growth during a conversation is legible as movement.
      node = {
        ...raw,
        x: width / 2 + (Math.random() - 0.5) * 60,
        y: height / 2 + (Math.random() - 0.5) * 60,
        vx: 0,
        vy: 0,
        born: performance.now(),
      };
    }
    next.push(node);
    byId.set(node.id, node);
  });

  sim.nodes = next;
  sim.byId = byId;
  sim.edges = field.edges
    .map((edge) => ({ ...edge, a: byId.get(edge.source), b: byId.get(edge.target) }))
    .filter((edge) => edge.a && edge.b);

  if (firstLoad && sim.nodes.length) {
    // An existing corpus should already be readable when the pane appears,
    // rather than visibly untangling itself for several seconds. Only material
    // that arrives later is worth animating.
    sim.alpha = 1;
    for (let i = 0; i < 400; i += 1) step();
  }

  $("field-empty").hidden = sim.nodes.length > 0;
}

function kick() {
  sim.alpha = 1;
  if (!sim.frame) sim.frame = requestAnimationFrame(tick);
}

function tick() {
  step();
  drawField();
  sim.alpha *= 0.992;
  if (sim.alpha > 0.02) {
    sim.frame = requestAnimationFrame(tick);
  } else {
    sim.frame = null;
  }
}

function step() {
  const svg = $("field-graph");
  const width = svg.clientWidth || 460;
  const height = svg.clientHeight || 460;
  const nodes = sim.nodes;

  // Repulsion. O(n²) is fine at this scale and keeps the code readable.
  for (let i = 0; i < nodes.length; i += 1) {
    for (let j = i + 1; j < nodes.length; j += 1) {
      const a = nodes[i];
      const b = nodes[j];
      let dx = b.x - a.x;
      let dy = b.y - a.y;
      let dist = Math.hypot(dx, dy) || 0.01;
      // Conversations hold each other at arm's length over a long range, so
      // each becomes a legible cluster instead of one central knot. Everything
      // else repels locally.
      const bothConversations = a.type === "conversation" && b.type === "conversation";
      const range = bothConversations ? 520 : 210;
      if (dist > range) continue;
      // Capped: an uncapped inverse-square term at near-zero distance throws
      // nodes across the canvas and they never recover.
      const push = bothConversations
        ? Math.min(5.5, 24000 / (dist * dist))
        : Math.min(3.2, 620 / (dist * dist));
      dx /= dist;
      dy /= dist;
      a.vx -= dx * push;
      a.vy -= dy * push;
      b.vx += dx * push;
      b.vy += dy * push;
    }
  }

  // Springs along edges.
  sim.edges.forEach((edge) => {
    const dx = edge.b.x - edge.a.x;
    const dy = edge.b.y - edge.a.y;
    const dist = Math.hypot(dx, dy) || 0.01;
    const rest = edge.a.type === "conversation" || edge.b.type === "conversation" ? 80 : 52;
    // Springs have to dominate repulsion, otherwise the field never clusters
    // and reads as noise rather than as conversations sharing material.
    const force = (dist - rest) * 0.045;
    const ux = (dx / dist) * force;
    const uy = (dy / dist) * force;
    edge.a.vx += ux;
    edge.a.vy += uy;
    edge.b.vx -= ux;
    edge.b.vy -= uy;
  });

  // Gentle centring so the field does not drift off-canvas.
  nodes.forEach((node) => {
    node.vx += (width / 2 - node.x) * 0.0038;
    node.vy += (height / 2 - node.y) * 0.0038;
    node.vx *= 0.82;
    node.vy *= 0.82;
    node.x += node.vx * Math.max(0.35, sim.alpha);
    node.y += node.vy * Math.max(0.35, sim.alpha);
    const r = radiusFor(node) + 14;
    node.x = Math.min(width - r, Math.max(r, node.x));
    node.y = Math.min(height - r, Math.max(r, node.y));
  });
}

function drawField() {
  const svg = $("field-graph");
  const now = performance.now();
  const parts = [];

  sim.edges.forEach((edge) => {
    const dim = state.selectedNode && !touches(edge, state.selectedNode);
    parts.push(
      `<line class="edge${dim ? " dim" : ""}" x1="${edge.a.x.toFixed(1)}" y1="${edge.a.y.toFixed(1)}" x2="${edge.b.x.toFixed(1)}" y2="${edge.b.y.toFixed(1)}" />`
    );
  });

  sim.nodes.forEach((node) => {
    const age = now - node.born;
    const grow = Math.min(1, age / 700);
    const r = radiusFor(node) * (0.2 + 0.8 * grow);
    const selected = state.selectedNode?.id === node.id;
    const dim = state.selectedNode && !selected && !connected(node, state.selectedNode);
    const shared = (node.conversations || []).length > 1 && !NODE_RADIUS[node.type];
    const classes = [
      "node",
      `node-${node.type}`,
      selected ? "selected" : "",
      dim ? "dim" : "",
      shared ? "shared" : "",
      node.marks?.length ? "marked" : "",
    ]
      .filter(Boolean)
      .join(" ");
    if (age < 900) {
      const pulse = 1 - age / 900;
      parts.push(
        `<circle class="pulse" cx="${node.x.toFixed(1)}" cy="${node.y.toFixed(1)}" r="${(r + 14 * pulse).toFixed(1)}" opacity="${(pulse * 0.35).toFixed(2)}" />`
      );
    }
    parts.push(
      `<circle class="${classes}" data-node="${escapeHtml(node.id)}" cx="${node.x.toFixed(1)}" cy="${node.y.toFixed(1)}" r="${r.toFixed(1)}"><title>${escapeHtml(`${TYPE_LABELS[node.type] || node.type}: ${short(node.label, 90)}`)}</title></circle>`
    );
  });

  // Labels only where they carry the argument: the conversations themselves,
  // whatever several conversations share, and the current selection. Shared
  // entities win collisions, since they are the point being made.
  const placed = [];
  const candidates = sim.nodes
    .map((node) => ({
      node,
      shared: (node.conversations || []).length > 1 && !NODE_RADIUS[node.type],
      selected: state.selectedNode?.id === node.id,
    }))
    .filter(({ node, shared, selected }) => {
      if (!shared && !selected && node.type !== "conversation") return false;
      return !(state.selectedNode && !selected && !connected(node, state.selectedNode));
    })
    .sort((a, b) => Number(b.selected) - Number(a.selected) || Number(b.shared) - Number(a.shared));

  const width = svg.clientWidth || 460;
  candidates.forEach(({ node }) => {
    const x = node.x;
    const y = node.y - radiusFor(node) - 5;
    if (placed.some((p) => Math.abs(p.x - x) < 74 && Math.abs(p.y - y) < 12)) return;
    placed.push({ x, y });
    const text = node.type === "recollection" ? short(node.label, 26) : short(node.label, 22);
    // Anchor away from the panel edges so labels are never clipped.
    const anchor = x < 80 ? "start" : x > width - 80 ? "end" : "middle";
    parts.push(
      `<text class="node-label label-${node.type}" text-anchor="${anchor}" x="${x.toFixed(1)}" y="${y.toFixed(1)}">${escapeHtml(text)}</text>`
    );
  });

  svg.innerHTML = parts.join("");
}

function touches(edge, node) {
  return edge.source === node.id || edge.target === node.id;
}

function connected(node, other) {
  return sim.edges.some(
    (edge) =>
      (edge.source === node.id && edge.target === other.id) ||
      (edge.target === node.id && edge.source === other.id)
  );
}

function renderCounters(field) {
  const c = field.counts;
  $("field-counters").innerHTML = `
    <span><b>${c.conversaciones}</b> conversaciones</span>
    <span><b>${c.recuerdos}</b> recuerdos</span>
    <span><b>${c.entidades}</b> entidades</span>
    <span><b>${c.relaciones}</b> relaciones</span>
    ${c.compartidas ? `<span class="shared-count"><b>${c.compartidas}</b> compartidas entre conversaciones</span>` : ""}
  `;
}

function renderChips(field) {
  $("extracted-chips").innerHTML = field.extracted
    .map((x) => `<span class="chip chip-${x.type}">${escapeHtml(x.label)} <b>${x.count}</b></span>`)
    .join("");
}

function selectNode(nodeId) {
  const node = sim.byId.get(nodeId);
  state.selectedNode = state.selectedNode?.id === nodeId ? null : node || null;
  renderNodeDetail();
  renderConversation();
  drawField();
}

function renderNodeDetail() {
  const panel = $("node-detail");
  const node = state.selectedNode;
  if (!node) {
    panel.hidden = true;
    panel.innerHTML = "";
    return;
  }

  // Every node can be traced back to the words somebody actually said.
  const sources = (state.field?.nodes || []).filter(
    (candidate) =>
      candidate.type === "recollection" &&
      (node.type === "recollection"
        ? candidate.id === node.id
        : (node.recollections || []).includes(candidate.turn_id))
  );
  const conversations = new Set(sources.map((s) => s.session_id));
  const marks = node.marks?.length
    ? `<div class="detail-marks">${node.marks.map((m) => `<span class="mark">${escapeHtml(MARK_LABELS[m] || m)}</span>`).join("")}</div>`
    : "";

  panel.hidden = false;
  panel.innerHTML = `
    <div class="detail-head">
      <span class="detail-type type-${node.type}">${escapeHtml(TYPE_LABELS[node.type] || node.type)}</span>
      <button type="button" id="close-detail">cerrar</button>
    </div>
    <div class="detail-label">${escapeHtml(short(node.label, 140))}</div>
    ${marks}
    ${
      node.type !== "recollection" && conversations.size > 1
        ? `<div class="detail-reach">Aparece en ${conversations.size} conversaciones.</div>`
        : ""
    }
    <div class="detail-sources">
      ${
        sources.length
          ? sources
              .map(
                (s) => `<blockquote class="detail-quote${s.session_id === state.session?.id ? " current" : ""}">${escapeHtml(short(s.label, 190))}</blockquote>`
              )
              .join("")
          : '<p class="muted">Sin recuerdos asociados.</p>'
      }
    </div>
  `;
  $("close-detail").addEventListener("click", () => selectNode(node.id));
}

$("field-graph").addEventListener("click", (event) => {
  const target = event.target.closest("[data-node]");
  if (target) selectNode(target.dataset.node);
  else if (state.selectedNode) selectNode(state.selectedNode.id);
});

window.addEventListener("resize", () => kick());

function renderAudit() {
  if (!state.session) return;
  const events = state.session.events || [];
  const derived = state.session.derived_items || [];
  const active = derived.filter((i) => !i.withdrawn);
  const counts = {
    turnos: state.session.turns.length,
    interpretaciones: active.length,
    investigador: active.filter((i) => i.origin !== "modelo").length,
    modelo: active.filter((i) => i.origin === "modelo").length,
    retiradas: derived.filter((i) => i.withdrawn).length,
    ediciones: derived.reduce((n, i) => n + (i.revisions || []).length, 0),
  };

  $("audit-summary").innerHTML = `
    <div class="stat"><span class="stat-n">${counts.turnos}</span><span class="stat-l">turnos preservados</span></div>
    <div class="stat"><span class="stat-n">${counts.interpretaciones}</span><span class="stat-l">interpretaciones</span></div>
    <div class="stat"><span class="stat-n">${counts.investigador}</span><span class="stat-l">del investigador</span></div>
    <div class="stat"><span class="stat-n">${counts.modelo}</span><span class="stat-l">del modelo</span></div>
    <div class="stat"><span class="stat-n">${counts.retiradas}</span><span class="stat-l">retiradas</span></div>
    <div class="stat"><span class="stat-n">${counts.ediciones}</span><span class="stat-l">ediciones</span></div>
  `;

  $("audit-log").innerHTML = [...events]
    .reverse()
    .map((event) => {
      const label = ACTION_LABELS[event.action] || event.action;
      const model = event.detail?.model;
      return `
      <div class="log-entry actor-${escapeHtml(event.actor)}">
        <div class="log-head">
          <span class="log-actor">${escapeHtml(event.actor)}</span>
          <span class="log-action">${escapeHtml(label)}</span>
          <span class="log-time">${escapeHtml(clockTime(event.at))}</span>
        </div>
        <div class="log-summary">${escapeHtml(event.summary)}</div>
        ${model ? `<div class="log-detail">${escapeHtml(model)}${event.detail.temperature !== undefined ? ` · temperature ${escapeHtml(String(event.detail.temperature))}, top_p ${escapeHtml(String(event.detail.top_p))}` : ""}</div>` : ""}
      </div>`;
    })
    .join("");
}

function clockTime(iso) {
  const date = new Date(iso);
  return Number.isNaN(date.getTime()) ? iso : date.toLocaleTimeString("es-UY");
}

function short(value, n = 45) {
  const collapsed = String(value).replace(/\s+/g, " ").trim();
  return collapsed.length > n ? `${collapsed.slice(0, n)}…` : collapsed;
}

function escapeHtml(value) {
  return String(value)
    .replaceAll("&", "&amp;")
    .replaceAll("<", "&lt;")
    .replaceAll(">", "&gt;")
    .replaceAll('"', "&quot;")
    .replaceAll("'", "&#039;");
}

function renderVoiceAvailability() {
  const config = state.config.voice || {};
  const status = $("voice-status");
  if (!config.asr_configured) {
    const missing = config.missing?.asr?.join(", ") || "componentes locales";
    status.textContent = `voz local no configurada: ${missing}`;
    return;
  }
  status.textContent = config.tts_configured
    ? `voz local · ${config.language || "es"} · entrada y salida`
    : `voz local · ${config.language || "es"} · sólo entrada`;
}

function setVoicePhase(phase, label) {
  state.voicePhase = phase;
  $("voice-status").textContent = label;
  const button = $("voice-toggle");
  button.classList.toggle("listening", phase === "listening");
  button.textContent = phase === "listening" ? "Detener" : "Hablar";
  const active = state.session?.status === "active" && !isRecorded();
  button.disabled = phase !== "idle" && phase !== "listening";
  if (phase === "idle") {
    button.disabled = !active || !state.config.llm_configured || !state.config.voice?.asr_configured;
    renderVoiceAvailability();
  }
}

async function startListening() {
  if (!navigator.mediaDevices?.getUserMedia || !window.MediaRecorder) {
    $("voice-status").textContent = "Este navegador no ofrece grabación de micrófono.";
    return;
  }
  try {
    voiceRuntime.stream = await navigator.mediaDevices.getUserMedia({ audio: true });
    voiceRuntime.context = new AudioContext();
    const source = voiceRuntime.context.createMediaStreamSource(voiceRuntime.stream);
    voiceRuntime.analyser = voiceRuntime.context.createAnalyser();
    voiceRuntime.analyser.fftSize = 1024;
    source.connect(voiceRuntime.analyser);

    const preferred = ["audio/webm;codecs=opus", "audio/mp4", "audio/webm"]
      .find((type) => MediaRecorder.isTypeSupported(type));
    voiceRuntime.recorder = preferred
      ? new MediaRecorder(voiceRuntime.stream, { mimeType: preferred })
      : new MediaRecorder(voiceRuntime.stream);
    voiceRuntime.chunks = [];
    voiceRuntime.heardSpeech = false;
    voiceRuntime.silentSince = 0;
    voiceRuntime.startedAt = performance.now();
    voiceRuntime.recorder.addEventListener("dataavailable", (event) => {
      if (event.data.size) voiceRuntime.chunks.push(event.data);
    });
    voiceRuntime.recorder.addEventListener("stop", processRecording, { once: true });
    voiceRuntime.recorder.start(250);
    setVoicePhase("listening", "Escuchando… hablá y dejá un breve silencio al terminar.");
    monitorSilence();
  } catch (error) {
    cleanupMicrophone();
    setVoicePhase("idle", "");
    $("voice-status").textContent = `No se pudo abrir el micrófono: ${error.message}`;
  }
}

function monitorSilence() {
  if (state.voicePhase !== "listening" || !voiceRuntime.analyser) return;
  const samples = new Uint8Array(voiceRuntime.analyser.fftSize);
  voiceRuntime.analyser.getByteTimeDomainData(samples);
  let sum = 0;
  for (const sample of samples) {
    const value = (sample - 128) / 128;
    sum += value * value;
  }
  const rms = Math.sqrt(sum / samples.length);
  const now = performance.now();
  if (rms > 0.025) {
    voiceRuntime.heardSpeech = true;
    voiceRuntime.silentSince = 0;
  } else if (voiceRuntime.heardSpeech) {
    if (!voiceRuntime.silentSince) voiceRuntime.silentSince = now;
    if (now - voiceRuntime.silentSince > 1250) return stopListening();
  }
  if (now - voiceRuntime.startedAt > 90000) return stopListening();
  voiceRuntime.frame = requestAnimationFrame(monitorSilence);
}

function stopListening() {
  if (voiceRuntime.recorder?.state === "recording") voiceRuntime.recorder.stop();
  if (voiceRuntime.frame) cancelAnimationFrame(voiceRuntime.frame);
}

function cleanupMicrophone() {
  if (voiceRuntime.frame) cancelAnimationFrame(voiceRuntime.frame);
  voiceRuntime.stream?.getTracks().forEach((track) => track.stop());
  if (voiceRuntime.context && voiceRuntime.context.state !== "closed") voiceRuntime.context.close();
  voiceRuntime.frame = null;
  voiceRuntime.stream = null;
  voiceRuntime.context = null;
  voiceRuntime.analyser = null;
  voiceRuntime.recorder = null;
}

async function processRecording() {
  const heardSpeech = voiceRuntime.heardSpeech;
  const mimeType = voiceRuntime.recorder?.mimeType || "audio/webm";
  const blob = new Blob(voiceRuntime.chunks, { type: mimeType });
  cleanupMicrophone();
  if (!heardSpeech || blob.size < 1000) {
    setVoicePhase("idle", "");
    $("voice-status").textContent = "No se detectó voz. Probá de nuevo.";
    return;
  }

  setVoicePhase("transcribing", "Transcribiendo localmente…");
  try {
    const response = await fetch(`/api/sessions/${state.session.id}/voice/transcribe`, {
      method: "POST",
      headers: { "Content-Type": mimeType },
      body: blob,
    });
    const result = await response.json();
    if (!response.ok) throw new Error(result.detail || `HTTP ${response.status}`);
    $("message").value = result.text;
    setVoicePhase("thinking", "Pensando…");
    await submitTurn(result.text, result.audio_id, true);
    $("message").value = "";
  } catch (error) {
    $("voice-status").textContent = `No se pudo procesar la voz: ${error.message}`;
  } finally {
    if (state.voicePhase !== "speaking") setVoicePhase("idle", "");
  }
}

async function speakText(text) {
  setVoicePhase("speaking", "Hablando… el micrófono está apagado.");
  const response = await fetch("/api/voice/speak", {
    method: "POST",
    headers: { "Content-Type": "application/json" },
    body: JSON.stringify({ text }),
  });
  if (!response.ok) {
    const payload = await response.json().catch(() => ({}));
    throw new Error(payload.detail || `HTTP ${response.status}`);
  }
  const url = URL.createObjectURL(await response.blob());
  try {
    const audio = new Audio(url);
    await audio.play();
    await new Promise((resolve, reject) => {
      audio.addEventListener("ended", resolve, { once: true });
      audio.addEventListener("error", reject, { once: true });
    });
  } finally {
    URL.revokeObjectURL(url);
    setVoicePhase("idle", "");
  }
}

$("new-session").addEventListener("click", async () => {
  state.selectedNode = null;
  setSession(await api("/api/sessions", { method: "POST", body: JSON.stringify({}) }));
  loadField();
  $("message").focus();
});

$("load-demo").addEventListener("click", async () => {
  state.selectedNode = null;
  try {
    setSession(await api("/api/sessions/demo", { method: "POST" }));
    loadField();
  } catch (error) {
    alert(error.message);
  }
});

async function submitTurn(text, audioId = "", speakReply = false) {
  if (!state.session || !state.config.llm_configured || isRecorded() || state.session.status !== "active") return null;
  if (!text.trim()) return null;
  $("send").disabled = true;
  $("send-status").textContent = "Pensando…";
  try {
    const result = await api(`/api/sessions/${state.session.id}/turns`, {
      method: "POST",
      body: JSON.stringify({ text, audio_id: audioId }),
    });
    setSession(result.session);
    $("send-status").textContent = "";
    // Extraction runs behind the reply, so the field fills in shortly after.
    watchField();
    if (speakReply && result.assistant_turn && state.config.voice?.tts_configured) {
      await speakText(result.assistant_turn.text);
    }
    return result;
  } catch (error) {
    if (error.payload?.session) setSession(error.payload.session);
    $("send-status").textContent = `No se pudo generar respuesta: ${error.message}`;
    return null;
  } finally {
    $("send").disabled = !state.config.llm_configured || isRecorded() || state.session?.status !== "active";
    $("message").focus();
  }
}

let watchTimers = [];
function watchField() {
  watchTimers.forEach(clearTimeout);
  // Extraction takes a few seconds on a local model; look a few times rather
  // than polling forever.
  watchTimers = [2000, 5000, 9000, 14000, 22000].map((delay) => setTimeout(loadField, delay));
}

$("composer").addEventListener("submit", async (event) => {
  event.preventDefault();
  const text = $("message").value;
  if (!text.trim()) return;
  $("message").value = "";
  await submitTurn(text);
});

$("message").addEventListener("keydown", (event) => {
  if (event.key === "Enter" && !event.shiftKey) {
    event.preventDefault();
    $("composer").requestSubmit();
  }
});

$("export-json").addEventListener("click", () => window.location.assign(`/api/sessions/${state.session.id}/export.json`));
$("export-md").addEventListener("click", () => window.location.assign(`/api/sessions/${state.session.id}/export.md`));

$("resume-session").addEventListener("click", async () => {
  try {
    setSession(await api(`/api/sessions/${state.session.id}/resume`, { method: "POST" }));
    $("message").focus();
  } catch (error) {
    alert(error.message);
  }
});

$("voice-toggle").addEventListener("click", () => {
  if (state.voicePhase === "listening") stopListening();
  else startListening();
});

$("open-record").addEventListener("click", () => {
  $("record-overlay").hidden = false;
});
$("close-record").addEventListener("click", () => {
  $("record-overlay").hidden = true;
});
$("record-overlay").addEventListener("click", (event) => {
  if (event.target === $("record-overlay")) $("record-overlay").hidden = true;
});

async function init() {
  state.config = await api("/api/config");
  const local = state.config.provenance?.local;
  $("model-status").textContent = state.config.llm_configured
    ? `${state.config.model}${local ? " · local" : ""}`
    : "modelo sin configurar";
  $("model-status").classList.toggle("status-local", Boolean(local));
  $("model-status").title = state.config.llm_configured
    ? `${state.config.provenance.endpoint}${local ? " — se ejecuta en esta máquina" : ""}`
    : "Definí LLM_MODEL y LLM_API_KEY u OPENAI_API_KEY";
  // ?session=ID opens a specific session directly, which is convenient when
  // showing a prepared session without clicking through to find it.
  const params = new URLSearchParams(location.search);
  const previous = params.get("session") || localStorage.getItem("ccm-current-session");
  if (previous) {
    try {
      setSession(await api(`/api/sessions/${previous}`));
    } catch (_) {
      localStorage.removeItem("ccm-current-session");
      render();
    }
  } else {
    render();
  }
  await loadField();
  // ?node=place:cerro opens straight to one entity and its recollections.
  const node = params.get("node");
  if (node && sim.byId.has(node)) selectNode(node);
}

init().catch((error) => {
  $("model-status").textContent = "error de inicio";
  console.error(error);
});
