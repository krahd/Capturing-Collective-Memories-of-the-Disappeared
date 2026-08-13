const state = {
  session: null,
  config: { llm_configured: false },
  voicePhase: "idle",
  // Set while a spoken turn is running so the microphone re-arms by itself.
  voiceContinuous: false,
  field: null,
  selectedNode: null,
  timeline: null,
  timelineYear: null,
  timelineSubject: null,
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
  // Generic on purpose: what extraction could not call a person or a place.
  entity: "entidad",
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
  // During a continuous exchange the button stays live: it is how the
  // participant ends it, and every render happens mid-loop.
  $("voice-toggle").disabled = state.voiceContinuous
    ? false
    : !live || !state.config.llm_configured || !state.config.voice?.asr_configured || state.voicePhase !== "idle";
  $("voice-toggle").textContent = state.voiceContinuous ? "Terminar" : "Hablar";
  if (state.voicePhase === "idle" && !state.voiceContinuous) renderVoiceAvailability();
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
    // Which conversational move produced a reply is implementation detail. It
    // is recorded on the turn and shown in `registro de la sesión`; beside the
    // conversation it makes the interface read as a research instrument.
    if (turn.record_kind === "non_testimony/control") {
      node.classList.add("non-testimony");
      const badge = document.createElement("span");
      badge.className = "turn-kind control";
      badge.textContent = "no testimonial";
      badge.title = turn.intent || "control";
      meta.appendChild(badge);
    } else if (turn.input_mode === "voice_asr") {
      const badge = document.createElement("span");
      badge.className = "turn-kind";
      badge.textContent = "voz";
      badge.title = "Transcripción ASR local del audio preservado";
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

// How long the two moments of growth stay visible. They are the argument, so
// they are slow enough to point at while talking.
const BIRTH_MS = 1400;
const CONVERGE_MS = 3000;

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
    // A conversation held while the chronology is open should reach it too,
    // without a reload.
    if (!$("timeline").hidden) refreshTimeline();
  } catch (error) {
    console.error("memory field", error);
  }
}

function animating(now) {
  return sim.nodes.some(
    (node) => now - node.born < BIRTH_MS || now - (node.convergedAt || -Infinity) < CONVERGE_MS
  );
}

function syncSimulation(field) {
  const svg = $("field-graph");
  const width = svg.clientWidth || 460;
  const height = svg.clientHeight || 460;
  const next = [];
  const byId = new Map();

  const firstLoad = sim.nodes.length === 0;
  const now = performance.now();
  field.nodes.forEach((raw, index) => {
    const existing = sim.byId.get(raw.id);
    let node;
    if (existing) {
      // A node another conversation has just reached is the moment worth
      // seeing: one person's account arriving at something somebody else
      // already said. Everything about that node then gets louder for a while.
      const reach = (existing.conversations || []).length;
      const held = (existing.recollections || []).length;
      node = Object.assign(existing, raw);
      if ((raw.conversations || []).length > reach) {
        node.convergedAt = now;
        node.convergenceKind = "conversation";
      } else if ((raw.recollections || []).length > held) {
        node.convergedAt = now;
        node.convergenceKind = "recollection";
      }
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
  // Keep drawing while anything is being born or converging, even after the
  // layout has settled: the animation is the explanation of the pipeline.
  if (sim.alpha > 0.02 || animating(performance.now())) {
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
    // An edge onto a node that has just been reached is the connection being
    // made, so it is drawn as the connection rather than as background.
    const fresh =
      now - (edge.b.convergedAt || -Infinity) < CONVERGE_MS ||
      now - edge.a.born < BIRTH_MS ||
      now - edge.b.born < BIRTH_MS;
    parts.push(
      `<line class="edge${dim ? " dim" : ""}${fresh && !dim ? " fresh" : ""}" x1="${edge.a.x.toFixed(1)}" y1="${edge.a.y.toFixed(1)}" x2="${edge.b.x.toFixed(1)}" y2="${edge.b.y.toFixed(1)}" />`
    );
  });

  sim.nodes.forEach((node) => {
    const age = now - node.born;
    const grow = Math.min(1, age / 700);
    const converging = now - (node.convergedAt || -Infinity);
    const collective = converging < CONVERGE_MS && node.convergenceKind === "conversation";
    // A node other conversations reach swells while it is being reached. The
    // swell is drawn, not simulated, so the layout does not lurch with it.
    const swell = collective ? 1 + 0.55 * Math.sin((Math.PI * converging) / CONVERGE_MS) : 1;
    const r = radiusFor(node) * (0.2 + 0.8 * grow) * swell;
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
      collective ? "converging" : "",
    ]
      .filter(Boolean)
      .join(" ");
    if (age < BIRTH_MS) {
      // Stage one and two both arrive this way: the recollection the moment the
      // words are stored, its people, places and dates once they are read out.
      const pulse = 1 - age / BIRTH_MS;
      parts.push(
        `<circle class="pulse" cx="${node.x.toFixed(1)}" cy="${node.y.toFixed(1)}" r="${(r + 20 * pulse).toFixed(1)}" opacity="${(pulse * 0.4).toFixed(2)}" />`
      );
    }
    if (collective) {
      // Stage three. Three rings leaving the node, staggered, so that a
      // conversation arriving at material somebody else already gave is the
      // loudest thing on screen.
      for (let i = 0; i < 3; i += 1) {
        const phase = (converging / CONVERGE_MS) * 1.7 - i * 0.24;
        if (phase <= 0 || phase >= 1) continue;
        parts.push(
          `<circle class="converge-ring" cx="${node.x.toFixed(1)}" cy="${node.y.toFixed(1)}" r="${(r + 46 * phase).toFixed(1)}" opacity="${((1 - phase) * 0.55).toFixed(2)}" />`
        );
      }
    }
    parts.push(
      `<circle class="${classes}" data-node="${escapeHtml(node.id)}" cx="${node.x.toFixed(1)}" cy="${node.y.toFixed(1)}" r="${r.toFixed(1)}"><title>${escapeHtml(`${TYPE_LABELS[node.type] || node.type}: ${short(node.label, 90)}`)}</title></circle>`
    );
  });

  // Labels only where they carry the argument: the conversations themselves,
  // whatever several conversations share, and the current selection. A node
  // being reached right now outranks all of them — if it is not named while it
  // pulses, the moment does not read.
  const placed = [];
  const candidates = sim.nodes
    .map((node) => ({
      node,
      converging: now - (node.convergedAt || -Infinity) < CONVERGE_MS,
      shared: (node.conversations || []).length > 1 && !NODE_RADIUS[node.type],
      selected: state.selectedNode?.id === node.id,
    }))
    .filter(({ node, shared, selected, converging }) => {
      if (!shared && !selected && !converging && node.type !== "conversation") return false;
      return !(state.selectedNode && !selected && !connected(node, state.selectedNode));
    })
    .sort(
      (a, b) =>
        Number(b.converging) - Number(a.converging) ||
        Number(b.selected) - Number(a.selected) ||
        Number(b.shared) - Number(a.shared)
    );

  const width = svg.clientWidth || 460;
  candidates.forEach(({ node, converging }) => {
    const x = node.x;
    const y = node.y - radiusFor(node) - (converging ? 12 : 5);
    if (placed.some((p) => Math.abs(p.x - x) < 74 && Math.abs(p.y - y) < 12)) return;
    placed.push({ x, y });
    const text = node.type === "recollection" ? short(node.label, 26) : short(node.label, 22);
    // Anchor away from the panel edges so labels are never clipped.
    const anchor = x < 80 ? "start" : x > width - 80 ? "end" : "middle";
    const reach = (node.conversations || []).length;
    parts.push(
      `<text class="node-label label-${node.type}${converging ? " converging" : ""}" text-anchor="${anchor}" x="${x.toFixed(1)}" y="${y.toFixed(1)}">${escapeHtml(text)}</text>`
    );
    if (converging && node.convergenceKind === "conversation" && reach > 1) {
      parts.push(
        `<text class="node-reach" text-anchor="${anchor}" x="${x.toFixed(1)}" y="${(y - 11).toFixed(1)}">${reach} conversaciones</text>`
      );
    }
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

/* ------------------------------------------------------------------ *
 * Cronología.
 *
 * The point is not that a timeline can be drawn. It is that one can be drawn
 * *without first deciding which date is right*: a subject two people date
 * differently sits at both years, and each year hands back the exact words.
 * ------------------------------------------------------------------ */

async function refreshTimeline() {
  try {
    state.timeline = await api("/api/timeline");
  } catch (error) {
    console.error("timeline", error);
    return false;
  }
  renderTimeline();
  return true;
}

async function openTimeline() {
  state.timelineYear = null;
  state.timelineSubject = null;
  $("timeline").hidden = false;
  $("field-graph").style.visibility = "hidden";
  $("node-detail").hidden = true;
  $("open-timeline").setAttribute("aria-pressed", "true");
  // The panel has to exist before the axis can be measured for layout.
  if (!(await refreshTimeline())) closeTimeline();
}

function closeTimeline() {
  $("timeline").hidden = true;
  $("field-graph").style.visibility = "";
  $("open-timeline").setAttribute("aria-pressed", "false");
  renderNodeDetail();
  kick();
}

function renderTimeline() {
  const data = state.timeline;
  if (!data) return;
  const points = data.points;
  const counts = data.counts;
  $("timeline-counts").textContent = points.length
    ? `${counts["años"]} años · ${counts["recuerdos_fechados"]} recuerdos fechados · ${counts["sin_año"]} sin año ubicable`
    : "";

  const svg = $("timeline-axis");
  const width = svg.clientWidth || 420;
  const height = 132;
  const pad = 34;
  if (!points.length) {
    svg.innerHTML = "";
    $("timeline-detail").innerHTML =
      '<p class="muted">Todavía no hay fechas ubicables en un año. Las conversaciones dicen «después», «los domingos» y cosas así, que la cronología conserva sin inventarles un año.</p>';
    return;
  }

  // Positioned by year, not by rank: the gap between 1976 and 1979 is a gap.
  const first = points[0].year;
  const last = points[points.length - 1].year;
  const span = Math.max(1, last - first);
  const at = (year) => pad + ((year - first) / span) * (width - 2 * pad);
  const baseline = height - 46;
  const maxHeld = Math.max(...points.map((p) => p.recollections.length));
  const parts = [
    `<line class="axis" x1="${pad}" y1="${baseline}" x2="${width - pad}" y2="${baseline}" />`,
  ];

  // Arcs over the axis for subjects that are dated more than one way. Not
  // labelled "contradiction": reunions that ran for years look identical from
  // here. The view shows that it happened and hands over the words.
  const shown = data.divergences.slice(0, 4);
  // Stacked within the height available, so a fourth arc cannot climb off the
  // top of the canvas and take its label with it.
  const headroom = (baseline - 14) / 2;
  const arcs = shown.map((divergence, index) => {
    const from = at(divergence.years[0]);
    const to = at(divergence.years[divergence.years.length - 1]);
    const lift = (headroom * (index + 1)) / shown.length;
    return {
      divergence,
      middle: (from + to) / 2,
      apex: baseline - lift - 3,
      active: state.timelineSubject === divergence.id,
      path: `M ${from.toFixed(1)} ${baseline} Q ${((from + to) / 2).toFixed(1)} ${(baseline - lift * 2).toFixed(1)} ${to.toFixed(1)} ${baseline}`,
    };
  });
  // A dashed hairline is not a target, so every arc gets an invisible fat twin.
  // All of them go underneath, or one arc's hit area swallows the next arc's
  // label — SVG hit-testing follows paint order and the last drawn wins.
  arcs.forEach(({ divergence, path }) => {
    parts.push(
      `<path class="divergence-hit" data-subject="${escapeHtml(divergence.id)}" d="${path}" />`
    );
  });
  arcs.forEach(({ divergence, path, active, middle, apex }) => {
    parts.push(
      `<path class="divergence${active ? " active" : ""}" d="${path}" />`,
      `<text class="divergence-label${active ? " active" : ""}" data-subject="${escapeHtml(divergence.id)}" text-anchor="middle" x="${middle.toFixed(1)}" y="${apex.toFixed(1)}">${escapeHtml(short(divergence.subject, 22))}</text>`
    );
  });

  points.forEach((point) => {
    const x = at(point.year);
    const r = 4 + 4 * Math.sqrt(point.recollections.length / Math.max(1, maxHeld));
    const active = state.timelineYear === point.year;
    parts.push(
      `<circle class="timeline-point${active ? " active" : ""}" data-year="${point.year}" cx="${x.toFixed(1)}" cy="${baseline}" r="${r.toFixed(1)}"><title>${point.recollections.length} recuerdo(s)</title></circle>`,
      `<text class="timeline-year${active ? " active" : ""}" data-year="${point.year}" text-anchor="middle" x="${x.toFixed(1)}" y="${baseline + 20}">${point.year}</text>`,
      `<text class="timeline-count" text-anchor="middle" x="${x.toFixed(1)}" y="${baseline + 32}">${point.recollections.length}</text>`
    );
  });

  svg.setAttribute("viewBox", `0 0 ${width} ${height}`);
  svg.innerHTML = parts.join("");
  renderTimelineDetail();
}

function renderTimelineDetail() {
  const data = state.timeline;
  const panel = $("timeline-detail");
  const subject = data.divergences.find((d) => d.id === state.timelineSubject);

  if (subject) {
    const held = new Map(data.points.map((p) => [p.year, p]));
    panel.innerHTML = `
      <div class="timeline-subject">
        <strong>${escapeHtml(subject.subject)}</strong>
        <span class="muted">aparece fechado en ${subject.years.join(" y ")}. La cronología no resuelve la diferencia.</span>
      </div>
      ${subject.years
        .map((year) => {
          const turns = subject.by_year[String(year)] || [];
          const sources = (held.get(year)?.recollections || []).filter((r) =>
            turns.includes(r.turn_id)
          );
          return `<div class="timeline-year-block"><span class="timeline-year-tag">${year}</span>${sources
            .map(quoteRecollection)
            .join("")}</div>`;
        })
        .join("")}
    `;
    return;
  }

  const point = data.points.find((p) => p.year === state.timelineYear);
  if (!point) {
    const undated = data.undated.length
      ? `<p class="muted">Sin año ubicable: ${data.undated
          .map((item) => `«${escapeHtml(item.label)}»`)
          .join(", ")}. Se conservan; no se les inventa una fecha.</p>`
      : "";
    panel.innerHTML = `<p class="muted">Tocá un año para leer los recuerdos que lo nombran.${
      data.divergences.length
        ? " Los arcos unen lo que quedó fechado de más de una manera."
        : ""
    }</p>${undated}`;
    return;
  }

  panel.innerHTML = `
    <div class="timeline-subject">
      <strong>${point.year}</strong>
      <span class="muted">${point.recollections.length} recuerdo(s) en ${point.conversations.length} conversación(es), a partir de: ${point.labels
        .map((label) => `«${escapeHtml(short(label, 46))}»`)
        .join(", ")}</span>
    </div>
    ${point.recollections.map(quoteRecollection).join("")}
  `;
}

function quoteRecollection(source) {
  const marks = (source.marks || [])
    .map((mark) => `<span class="mark">${escapeHtml(MARK_LABELS[mark] || mark)}</span>`)
    .join("");
  return `
    <blockquote class="detail-quote${source.session_id === state.session?.id ? " current" : ""}">
      <span class="quote-source">${escapeHtml(source.conversation || "conversación")}</span>
      ${escapeHtml(short(source.text, 220))}
      ${marks ? `<span class="detail-marks">${marks}</span>` : ""}
    </blockquote>
  `;
}

$("timeline-axis").addEventListener("click", (event) => {
  const subject = event.target.closest("[data-subject]");
  if (subject) {
    state.timelineSubject =
      state.timelineSubject === subject.dataset.subject ? null : subject.dataset.subject;
    state.timelineYear = null;
    renderTimeline();
    return;
  }
  const year = event.target.closest("[data-year]");
  if (!year) return;
  const value = Number(year.dataset.year);
  state.timelineYear = state.timelineYear === value ? null : value;
  state.timelineSubject = null;
  renderTimeline();
});

$("open-timeline").addEventListener("click", () => {
  if ($("timeline").hidden) openTimeline();
  else closeTimeline();
});
$("close-timeline").addEventListener("click", closeTimeline);

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
  // In a continuous exchange the button is the way out, not the way in.
  // Pressing it for every single utterance is what makes voice feel like a
  // form rather than a conversation.
  button.textContent = state.voiceContinuous ? "Terminar" : "Hablar";
  const active = state.session?.status === "active" && !isRecorded();
  button.disabled = state.voiceContinuous ? false : phase !== "idle" && phase !== "listening";
  if (phase === "idle" && !state.voiceContinuous) {
    button.disabled = !active || !state.config.llm_configured || !state.config.voice?.asr_configured;
    renderVoiceAvailability();
  }
}

function canListen() {
  return Boolean(
    state.session &&
      state.session.status === "active" &&
      !isRecorded() &&
      state.config.llm_configured &&
      state.config.voice?.asr_configured
  );
}

function endVoiceLoop(message) {
  state.voiceContinuous = false;
  setVoicePhase("idle", "");
  if (message) $("voice-status").textContent = message;
}

/** LISTEN → THINK → SPEAK → LISTEN, until the participant ends it. */
function rearmMicrophone() {
  if (!state.voiceContinuous) return endVoiceLoop("");
  if (!canListen()) return endVoiceLoop("");
  startListening();
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
    setVoicePhase(
      "listening",
      state.voiceContinuous ? "Escuchando… tomate el tiempo que quieras." : "Escuchando…"
    );
    monitorSilence();
  } catch (error) {
    cleanupMicrophone();
    endVoiceLoop(`No se pudo abrir el micrófono: ${error.message}`);
  }
}

// How long a pause has to last before the turn is taken as finished. This is
// demo turn detection, not archival VAD, and the number is a claim about the
// conversation rather than a technical default: a memory conversation is full
// of hesitation, and a threshold tuned for command-and-control speech cuts
// people off exactly where they are reaching for something.
const END_OF_TURN_SILENCE_MS = 2400;
// The microphone re-arms by itself after each reply. If nobody says anything at
// all, the loop ends rather than sitting open indefinitely.
const REARM_TIMEOUT_MS = 20000;
const MAX_TURN_MS = 120000;

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
    if (now - voiceRuntime.silentSince > END_OF_TURN_SILENCE_MS) return stopListening();
  } else if (state.voiceContinuous && now - voiceRuntime.startedAt > REARM_TIMEOUT_MS) {
    // Re-armed, and nobody spoke. Close the loop quietly.
    state.voiceContinuous = false;
    return stopListening();
  }
  if (now - voiceRuntime.startedAt > MAX_TURN_MS) return stopListening();
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
    endVoiceLoop(state.voiceContinuous ? "No se detectó voz. Tocá Hablar cuando quieras seguir." : "");
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
    // Half-duplex: the microphone was closed for synthesis and opens again on
    // its own. Nothing to press between turns.
    rearmMicrophone();
  } catch (error) {
    endVoiceLoop(`No se pudo procesar la voz: ${error.message}`);
  }
}

async function speakText(text) {
  setVoicePhase("speaking", "Hablando…");
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
  // The words are preserved before anything is asked of the model, so the
  // recollection can appear while the reply is still being composed. Preserving
  // what somebody said does not depend on understanding it, and showing that
  // first is the whole point of separating the stages.
  watchStorage();
  try {
    const result = await api(`/api/sessions/${state.session.id}/turns`, {
      method: "POST",
      body: JSON.stringify({ text, audio_id: audioId }),
    });
    setSession(result.session);
    $("send-status").textContent = "";
    // Interpretation follows on its own, once the conversational model is free.
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

let storageTimers = [];
function watchStorage() {
  storageTimers.forEach(clearTimeout);
  // The turn is written before classification, so a look shortly after the
  // request is issued already finds it. Two looks, because the first can lose
  // the race and there is nothing to gain from polling for it.
  storageTimers = [500, 1400].map((delay) => setTimeout(loadField, delay));
}

let watchTimers = [];
function watchField() {
  watchTimers.forEach(clearTimeout);
  // Two distinct moments, not one delayed one.
  //
  // The words are preserved the instant the turn is stored, so the recollection
  // node is drawn now — before anything has been read out of it. Interpretation
  // arrives afterwards, on its own, when the conversational model is free, and
  // brings the people, places and dates with it. Whatever the corpus already
  // held then lights up as this conversation reaches it.
  //
  // Showing both at once would collapse "stored", "interpreted" and "connected"
  // into a single unexplained event.
  loadField();
  watchTimers = [2000, 4000, 7000, 11000, 16000, 24000, 34000].map((delay) =>
    setTimeout(loadField, delay)
  );
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
  if (state.voiceContinuous) {
    // Ends the exchange. A turn already in flight finishes and does not re-arm.
    state.voiceContinuous = false;
    if (state.voicePhase === "listening") stopListening();
    else setVoicePhase(state.voicePhase, $("voice-status").textContent);
    return;
  }
  state.voiceContinuous = true;
  startListening();
});

$("open-record").addEventListener("click", () => {
  $("record-overlay").hidden = false;
});
// The badge is the claim; the record is where the claim is substantiated.
$("model-status").addEventListener("click", () => {
  $("record-overlay").hidden = false;
});
$("close-record").addEventListener("click", () => {
  $("record-overlay").hidden = true;
});
$("record-overlay").addEventListener("click", (event) => {
  if (event.target === $("record-overlay")) $("record-overlay").hidden = true;
});

function renderModelStatus() {
  // What matters in the room is that nothing leaves the machine. The model
  // identifier is an implementation detail and belongs in the record, which
  // this badge opens.
  const badge = $("model-status");
  const local = state.config.provenance?.local;
  badge.textContent = !state.config.llm_configured
    ? "modelo sin configurar"
    : local
      ? "LOCAL"
      : "remoto";
  badge.classList.toggle("status-local", Boolean(local));
  badge.classList.toggle("status-remote", state.config.llm_configured && !local);
  badge.title = state.config.llm_configured
    ? `${state.config.model} · ${state.config.provenance.endpoint}${local ? " — se ejecuta en esta máquina" : " — sale de esta máquina"}`
    : "Definí LLM_MODEL y LLM_API_KEY u OPENAI_API_KEY";
}

function renderRecordModels() {
  const panel = $("record-models");
  if (!state.config.llm_configured) {
    panel.innerHTML = '<p class="muted">Sin modelo configurado.</p>';
    return;
  }
  const conversation = state.config.provenance;
  const extraction = state.config.extraction_provenance || conversation;
  const line = (role, provenance) => `
    <div class="record-model">
      <span class="record-model-role">${role}</span>
      <span class="record-model-id">${escapeHtml(provenance.model || "—")}</span>
      <span class="record-model-where">${escapeHtml(provenance.endpoint || "")}${provenance.local ? " · en esta máquina" : ""}</span>
    </div>`;
  panel.innerHTML =
    line("conversación", conversation) +
    (extraction.model !== conversation.model ? line("extracción", extraction) : "");
}

async function init() {
  state.config = await api("/api/config");
  renderModelStatus();
  renderRecordModels();
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
