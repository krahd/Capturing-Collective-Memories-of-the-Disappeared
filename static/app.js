const state = {
  session: null,
  selected: new Set(),
  config: { llm_configured: false },
  // Provenance made visible: the derived item whose source turns are lit up,
  // and the turn whose interpretations are being isolated.
  focusedItem: null,
  turnFilter: null,
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
};

const KIND_LABELS = {
  entity: "personas y entidades",
  event: "eventos",
  place: "lugares",
  time: "tiempo",
  theme: "temas",
  uncertainty: "incertidumbre",
  hearsay: "de oídas",
  correction: "correcciones",
  relation: "relaciones",
  other: "otros",
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

function selectedTurnIds() {
  return [...state.selected];
}

function isRecorded() {
  return Boolean(state.session?.is_recorded);
}

function turnById(id) {
  return state.session?.turns.find((t) => t.id === id) || null;
}

function setSession(session) {
  state.session = session;
  if (session?.id) localStorage.setItem("ccm-current-session", session.id);
  const existing = new Set(session.turns.map((t) => t.id));
  state.selected = new Set([...state.selected].filter((id) => existing.has(id)));
  if (state.turnFilter && !existing.has(state.turnFilter)) state.turnFilter = null;
  render();
}

function render() {
  renderConversation();
  renderWorkbench();
  renderAudit();
  const ready = Boolean(state.session);
  const live = ready && !isRecorded();
  $("recorded-banner").hidden = !isRecorded();
  $("message").disabled = !live;
  $("message").placeholder = isRecorded() ? "Transcripción grabada: no admite turnos nuevos." : "Escribí acá…";
  $("send").disabled = !live || !state.config.llm_configured;
  $("export-json").disabled = !ready;
  $("export-md").disabled = !ready;
  const hasSelection = selectedTurnIds().length > 0;
  $("add-annotation").disabled = !hasSelection;
  $("add-derived").disabled = !hasSelection;
  $("auto-extract").disabled = !hasSelection || !state.config.llm_configured;
}

function derivedForTurn(turnId) {
  return (state.session?.derived_items || []).filter((i) => i.source_turn_ids.includes(turnId));
}

function renderConversation() {
  const root = $("conversation");
  root.innerHTML = "";
  if (!state.session) {
    root.innerHTML = '<p class="muted">Creá una conversación para empezar.</p>';
    return;
  }
  const focused = state.focusedItem
    ? state.session.derived_items.find((i) => i.id === state.focusedItem)
    : null;
  const lit = new Set(focused ? focused.source_turn_ids : []);

  const template = $("turn-template");
  state.session.turns.forEach((turn) => {
    const node = template.content.firstElementChild.cloneNode(true);
    node.classList.add(turn.role);
    node.dataset.turnId = turn.id;
    if (lit.has(turn.id)) node.classList.add("lit");
    if (state.turnFilter === turn.id) node.classList.add("filtered");

    const checkbox = node.querySelector("input");
    checkbox.checked = state.selected.has(turn.id);
    checkbox.addEventListener("change", () => {
      checkbox.checked ? state.selected.add(turn.id) : state.selected.delete(turn.id);
      render();
    });

    const meta = node.querySelector(".turn-meta");
    meta.textContent = `${turn.role === "user" ? "Participante" : "Sistema"} · ${turn.id}`;

    const attached = derivedForTurn(turn.id);
    if (attached.length) {
      const trace = document.createElement("button");
      trace.type = "button";
      trace.className = "trace-button";
      trace.textContent = `${attached.length} interpretación${attached.length === 1 ? "" : "es"}`;
      trace.title = "Ver el material derivado que cita este turno";
      trace.addEventListener("click", () => {
        state.turnFilter = state.turnFilter === turn.id ? null : turn.id;
        state.focusedItem = null;
        showTab("derived");
        render();
      });
      meta.appendChild(trace);
    }

    node.querySelector(".turn-text").textContent = turn.text;
    root.appendChild(node);
  });

  const target = focused ? root.querySelector(".turn.lit") : null;
  if (target) target.scrollIntoView({ behavior: "smooth", block: "center" });
  else root.scrollTop = root.scrollHeight;
}

function originBadge(item) {
  const isModel = item.origin === "modelo";
  const model = item.origin_detail?.model;
  const label = isModel ? `modelo${model ? ` · ${model}` : ""}` : "investigador";
  const title = isModel
    ? `Producido por el modelo ${model || "(sin identificar)"}` +
      (item.origin_detail?.temperature !== undefined
        ? ` · temperature ${item.origin_detail.temperature}, top_p ${item.origin_detail.top_p}, max_tokens ${item.origin_detail.max_tokens}`
        : "")
    : "Escrito por el investigador";
  return `<span class="badge ${isModel ? "badge-model" : "badge-researcher"}" title="${escapeHtml(title)}">${escapeHtml(label)}</span>`;
}

function sourceRefs(item) {
  return item.source_turn_ids
    .map((id) => {
      const turn = turnById(id);
      const text = turn ? `«${short(turn.text, 38)}»` : id;
      return `<button type="button" class="ref-chip" data-goto="${escapeHtml(id)}" title="${escapeHtml(id)}">${escapeHtml(text)}</button>`;
    })
    .join(" ");
}

function renderWorkbench() {
  const ids = selectedTurnIds();
  $("selection-summary").textContent = ids.length
    ? `${ids.length} turno${ids.length === 1 ? "" : "s"} seleccionado${ids.length === 1 ? "" : "s"}.`
    : "No hay turnos seleccionados.";
  if (!state.session) return;

  $("annotations").innerHTML = state.session.annotations
    .map(
      (a) => `
    <div class="card"><strong>${escapeHtml(a.label)}</strong><div>${escapeHtml(a.note || "—")}</div><div class="refs">${sourceRefs(a)}</div></div>
  `
    )
    .join("");

  renderDerived();

  const relationOptions = [
    ...state.session.turns.map((t) => ({ id: t.id, label: `${t.role === "user" ? "turno participante" : "turno sistema"}: ${short(t.text)}` })),
    ...state.session.derived_items.map((i) => ({ id: i.id, label: `${i.kind}: ${short(i.text)}` })),
  ];
  [$("relation-source"), $("relation-target")].forEach((select) => {
    select.innerHTML = relationOptions.map((o) => `<option value="${o.id}">${escapeHtml(o.label)}</option>`).join("");
  });
  $("add-relation").disabled = relationOptions.length < 2;
  $("relations").innerHTML = state.session.relations
    .map(
      (r) => `
    <div class="card"><strong>${escapeHtml(r.relation_type)}</strong><div class="refs">${escapeHtml(r.source_id)} → ${escapeHtml(r.target_id)}</div><div>${escapeHtml(r.note || "")}</div></div>
  `
    )
    .join("");
}

function renderDerived() {
  const filterNote = $("derived-filter");
  let items = state.session.derived_items;
  if (state.turnFilter) {
    const turn = turnById(state.turnFilter);
    items = derivedForTurn(state.turnFilter);
    filterNote.hidden = false;
    filterNote.innerHTML = `Mostrando sólo lo que cita «${escapeHtml(short(turn?.text || "", 50))}» <button type="button" id="clear-filter">ver todo</button>`;
  } else {
    filterNote.hidden = true;
    filterNote.innerHTML = "";
  }

  // Grouped by kind so a session reads as a small constellation of people,
  // places, times and themes rather than an undifferentiated list.
  const groups = new Map();
  items.forEach((item) => {
    if (!groups.has(item.kind)) groups.set(item.kind, []);
    groups.get(item.kind).push(item);
  });

  const html = [...groups.entries()]
    .map(([kind, group]) => {
      const cards = group.map((i) => derivedCard(i)).join("");
      return `<div class="group"><h2 class="group-title">${escapeHtml(KIND_LABELS[kind] || kind)} <span class="group-count">${group.length}</span></h2>${cards}</div>`;
    })
    .join("");
  $("derived-items").innerHTML = html || '<p class="muted">Todavía no hay material derivado.</p>';

  attachDerivedHandlers();
}

function derivedCard(i) {
  const withdrawn = i.withdrawn;
  const revisions = (i.revisions || []).length;
  return `
    <div class="card derived ${withdrawn ? "withdrawn" : ""} ${state.focusedItem === i.id ? "focused" : ""}" data-derived-id="${i.id}">
      <div class="card-head" data-trace="${i.id}" title="Ver los turnos exactos que originaron esto">
        <strong>${escapeHtml(i.kind)}</strong>
        ${originBadge(i)}
        ${withdrawn ? '<span class="badge badge-withdrawn">retirada</span>' : ""}
        ${revisions ? `<span class="badge badge-revised" title="${revisions} cambio(s) registrado(s)">${revisions} revisión${revisions === 1 ? "" : "es"}</span>` : ""}
      </div>
      ${
        withdrawn
          ? `<div class="withdrawn-text">${escapeHtml(i.text)}</div>
             <div class="withdrawn-reason">Retirada, no eliminada${i.withdrawn_reason ? `: ${escapeHtml(i.withdrawn_reason)}` : "."}</div>`
          : `<textarea class="derived-edit-text" rows="3">${escapeHtml(i.text)}</textarea>
             <select class="derived-edit-status">
               ${["provisional", "reviewed", "disputed"].map((s) => `<option value="${s}" ${s === i.status ? "selected" : ""}>${s}</option>`).join("")}
             </select>
             <input class="derived-edit-note" value="${escapeHtml(i.note || "")}" placeholder="Nota" />
             <div class="row-actions">
               <button class="save-derived">Guardar</button>
               <button class="withdraw-derived">Retirar</button>
               <button class="delete-derived subtle">Eliminar</button>
             </div>`
      }
      ${revisions ? renderRevisions(i) : ""}
      <div class="refs">fuentes: ${sourceRefs(i)}</div>
    </div>
  `;
}

function renderRevisions(item) {
  const rows = item.revisions
    .map(
      (r) => `<li><span class="rev-field">${escapeHtml(r.field)}</span> «${escapeHtml(short(r.before, 40))}» → «${escapeHtml(short(r.after, 40))}»</li>`
    )
    .join("");
  return `<details class="revisions"><summary>historial de cambios</summary><ul>${rows}</ul></details>`;
}

function attachDerivedHandlers() {
  const clear = $("clear-filter");
  if (clear) {
    clear.addEventListener("click", () => {
      state.turnFilter = null;
      render();
    });
  }

  document.querySelectorAll("[data-trace]").forEach((head) => {
    head.addEventListener("click", () => {
      const id = head.dataset.trace;
      state.focusedItem = state.focusedItem === id ? null : id;
      render();
    });
  });

  document.querySelectorAll("[data-goto]").forEach((chip) => {
    chip.addEventListener("click", (event) => {
      event.stopPropagation();
      const node = document.querySelector(`.turn[data-turn-id="${chip.dataset.goto}"]`);
      if (node) {
        node.classList.add("lit");
        node.scrollIntoView({ behavior: "smooth", block: "center" });
      }
    });
  });

  document.querySelectorAll(".save-derived").forEach((button) => {
    button.addEventListener("click", async () => {
      const card = button.closest(".card");
      const id = card.dataset.derivedId;
      await mutate(`/api/sessions/${state.session.id}/derived/${id}`, {
        method: "PATCH",
        body: JSON.stringify({
          text: card.querySelector(".derived-edit-text").value,
          status: card.querySelector(".derived-edit-status").value,
          note: card.querySelector(".derived-edit-note").value,
        }),
      });
    });
  });

  document.querySelectorAll(".withdraw-derived").forEach((button) => {
    button.addEventListener("click", async () => {
      const card = button.closest(".card");
      const id = card.dataset.derivedId;
      const reason = prompt("¿Por qué se retira? Queda registrado junto al material.", "");
      if (reason === null) return;
      await mutate(`/api/sessions/${state.session.id}/derived/${id}/withdraw`, {
        method: "POST",
        body: JSON.stringify({ reason }),
      });
    });
  });

  document.querySelectorAll(".delete-derived").forEach((button) => {
    button.addEventListener("click", async () => {
      const card = button.closest(".card");
      const id = card.dataset.derivedId;
      if (!confirm("Eliminar definitivamente. El texto no se conserva; sólo queda constancia de que hubo una eliminación.\n\nPara conservar el material marcado, usá «Retirar».")) return;
      await mutate(`/api/sessions/${state.session.id}/derived/${id}`, { method: "DELETE" });
    });
  });
}

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

async function refreshSession() {
  if (!state.session) return;
  setSession(await api(`/api/sessions/${state.session.id}`));
}

async function mutate(url, options) {
  try {
    await api(url, options);
    await refreshSession();
  } catch (error) {
    alert(error.message);
  }
}

function showTab(name) {
  document.querySelectorAll(".tab").forEach((x) => x.classList.toggle("active", x.dataset.tab === name));
  document.querySelectorAll(".tab-panel").forEach((x) => x.classList.toggle("active", x.id === `tab-${name}`));
}

$("new-session").addEventListener("click", async () => {
  state.selected.clear();
  state.focusedItem = null;
  state.turnFilter = null;
  setSession(await api("/api/sessions", { method: "POST", body: JSON.stringify({}) }));
  $("message").focus();
});

$("load-demo").addEventListener("click", async () => {
  state.selected.clear();
  state.focusedItem = null;
  state.turnFilter = null;
  try {
    setSession(await api("/api/sessions/demo", { method: "POST" }));
  } catch (error) {
    alert(error.message);
  }
});

$("composer").addEventListener("submit", async (event) => {
  event.preventDefault();
  if (!state.session || !state.config.llm_configured || isRecorded()) return;
  const text = $("message").value;
  if (!text.trim()) return;
  $("message").value = "";
  $("send").disabled = true;
  $("send-status").textContent = "Pensando…";
  try {
    const result = await api(`/api/sessions/${state.session.id}/turns`, { method: "POST", body: JSON.stringify({ text }) });
    setSession(result.session);
    $("send-status").textContent = "";
  } catch (error) {
    if (error.payload?.session) setSession(error.payload.session);
    $("send-status").textContent = `No se pudo generar respuesta: ${error.message}`;
  } finally {
    $("send").disabled = !state.config.llm_configured || isRecorded();
    $("message").focus();
  }
});

$("message").addEventListener("keydown", (event) => {
  if (event.key === "Enter" && !event.shiftKey) {
    event.preventDefault();
    $("composer").requestSubmit();
  }
});

$("add-annotation").addEventListener("click", async () => {
  await mutate(`/api/sessions/${state.session.id}/annotations`, {
    method: "POST",
    body: JSON.stringify({
      source_turn_ids: selectedTurnIds(),
      label: $("annotation-label").value,
      note: $("annotation-note").value,
    }),
  });
  $("annotation-note").value = "";
});

$("add-derived").addEventListener("click", async () => {
  const text = $("derived-text").value.trim();
  if (!text) return;
  await mutate(`/api/sessions/${state.session.id}/derived`, {
    method: "POST",
    body: JSON.stringify({
      source_turn_ids: selectedTurnIds(),
      kind: $("derived-kind").value,
      text,
    }),
  });
  $("derived-text").value = "";
});

$("auto-extract").addEventListener("click", async () => {
  $("auto-extract").disabled = true;
  $("auto-extract").textContent = "Extrayendo…";
  try {
    await api(`/api/sessions/${state.session.id}/extract`, {
      method: "POST",
      body: JSON.stringify({ source_turn_ids: selectedTurnIds() }),
    });
    await refreshSession();
  } catch (error) {
    alert(error.message);
  } finally {
    $("auto-extract").textContent = "Extraer provisionalmente con el modelo";
    $("auto-extract").disabled = !state.config.llm_configured || selectedTurnIds().length === 0;
  }
});

$("add-relation").addEventListener("click", async () => {
  const source = $("relation-source").value;
  const target = $("relation-target").value;
  if (!source || !target || source === target) return alert("Elegí dos elementos distintos.");
  await mutate(`/api/sessions/${state.session.id}/relations`, {
    method: "POST",
    body: JSON.stringify({
      relation_type: $("relation-type").value,
      source_id: source,
      target_id: target,
      note: $("relation-note").value,
    }),
  });
  $("relation-note").value = "";
});

$("export-json").addEventListener("click", () => window.location.assign(`/api/sessions/${state.session.id}/export.json`));
$("export-md").addEventListener("click", () => window.location.assign(`/api/sessions/${state.session.id}/export.md`));

document.querySelectorAll(".tab").forEach((tab) => {
  tab.addEventListener("click", () => showTab(tab.dataset.tab));
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
  const requested = params.get("session");
  if (params.get("tab")) showTab(params.get("tab"));
  const previous = requested || localStorage.getItem("ccm-current-session");
  if (previous) {
    try {
      setSession(await api(`/api/sessions/${previous}`));
      return;
    } catch (_) {
      localStorage.removeItem("ccm-current-session");
    }
  }
  render();
}

init().catch((error) => {
  $("model-status").textContent = "error de inicio";
  console.error(error);
});
