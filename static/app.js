const state = {
  session: null,
  selected: new Set(),
  config: { llm_configured: false },
};

const $ = (id) => document.getElementById(id);

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

function setSession(session) {
  state.session = session;
  if (session?.id) localStorage.setItem("ccm-current-session", session.id);
  const existing = new Set(session.turns.map((t) => t.id));
  state.selected = new Set([...state.selected].filter((id) => existing.has(id)));
  render();
}

function render() {
  renderConversation();
  renderWorkbench();
  const ready = Boolean(state.session);
  $("message").disabled = !ready;
  $("send").disabled = !ready || !state.config.llm_configured;
  $("export-json").disabled = !ready;
  $("export-md").disabled = !ready;
  const hasSelection = selectedTurnIds().length > 0;
  $("add-annotation").disabled = !hasSelection;
  $("add-derived").disabled = !hasSelection;
  $("auto-extract").disabled = !hasSelection || !state.config.llm_configured;
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
    const checkbox = node.querySelector("input");
    checkbox.checked = state.selected.has(turn.id);
    checkbox.addEventListener("change", () => {
      checkbox.checked ? state.selected.add(turn.id) : state.selected.delete(turn.id);
      render();
    });
    node.querySelector(".turn-meta").textContent = `${turn.role === "user" ? "Vos" : "Conversación"} · ${turn.id}`;
    node.querySelector(".turn-text").textContent = turn.text;
    root.appendChild(node);
  });
  root.scrollTop = root.scrollHeight;
}

function renderWorkbench() {
  const ids = selectedTurnIds();
  $("selection-summary").textContent = ids.length ? `${ids.length} turno${ids.length === 1 ? "" : "s"} seleccionado${ids.length === 1 ? "" : "s"}.` : "No hay turnos seleccionados.";
  if (!state.session) return;

  $("annotations").innerHTML = state.session.annotations.map((a) => `
    <div class="card"><strong>${escapeHtml(a.label)}</strong><div>${escapeHtml(a.note || "—")}</div><div class="refs">${a.source_turn_ids.map(escapeHtml).join(", ")}</div></div>
  `).join("");

  $("derived-items").innerHTML = state.session.derived_items.map((i) => `
    <div class="card" data-derived-id="${i.id}">
      <strong>${escapeHtml(i.kind)} · ${escapeHtml(i.status)}</strong>
      <textarea class="derived-edit-text" rows="3">${escapeHtml(i.text)}</textarea>
      <select class="derived-edit-status">
        ${["provisional", "reviewed", "disputed", "withdrawn"].map((s) => `<option value="${s}" ${s === i.status ? "selected" : ""}>${s}</option>`).join("")}
      </select>
      <input class="derived-edit-note" value="${escapeHtml(i.note || "")}" placeholder="Nota" />
      <button class="save-derived">Guardar cambios</button>
      <div class="refs">fuentes: ${i.source_turn_ids.map(escapeHtml).join(", ")}</div>
    </div>
  `).join("");

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

  const relationOptions = [
    ...state.session.turns.map((t) => ({ id: t.id, label: `${t.role === "user" ? "turno participante" : "turno sistema"}: ${short(t.text)}` })),
    ...state.session.derived_items.map((i) => ({ id: i.id, label: `${i.kind}: ${short(i.text)}` })),
  ];
  [$("relation-source"), $("relation-target")].forEach((select) => {
    select.innerHTML = relationOptions.map((o) => `<option value="${o.id}">${escapeHtml(o.label)}</option>`).join("");
  });
  $("add-relation").disabled = relationOptions.length < 2;
  $("relations").innerHTML = state.session.relations.map((r) => `
    <div class="card"><strong>${escapeHtml(r.relation_type)}</strong><div>${escapeHtml(r.source_id)} → ${escapeHtml(r.target_id)}</div><div>${escapeHtml(r.note || "")}</div></div>
  `).join("");
}

function short(value, n = 45) {
  return value.length > n ? `${value.slice(0, n)}…` : value;
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

$("new-session").addEventListener("click", async () => {
  state.selected.clear();
  setSession(await api("/api/sessions", { method: "POST", body: JSON.stringify({}) }));
  $("message").focus();
});

$("composer").addEventListener("submit", async (event) => {
  event.preventDefault();
  if (!state.session || !state.config.llm_configured) return;
  const text = $("message").value;
  if (!text.trim()) return;
  $("message").value = "";
  $("send").disabled = true;
  $("send-status").textContent = "Pensando…";
  try {
    const result = await api(`/api/sessions/${state.session.id}/turns`, { method: "POST", body: JSON.stringify({ text }) });
    setSession(result.session);
  } catch (error) {
    if (error.payload?.session) setSession(error.payload.session);
    $("send-status").textContent = `No se pudo generar respuesta: ${error.message}`;
  } finally {
    $("send-status").textContent = "";
    $("send").disabled = !state.config.llm_configured;
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
  try {
    await api(`/api/sessions/${state.session.id}/extract`, {
      method: "POST",
      body: JSON.stringify({ source_turn_ids: selectedTurnIds() }),
    });
    await refreshSession();
  } catch (error) {
    alert(error.message);
  } finally {
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
  tab.addEventListener("click", () => {
    document.querySelectorAll(".tab").forEach((x) => x.classList.toggle("active", x === tab));
    document.querySelectorAll(".tab-panel").forEach((x) => x.classList.toggle("active", x.id === `tab-${tab.dataset.tab}`));
  });
});

async function init() {
  state.config = await api("/api/config");
  $("model-status").textContent = state.config.llm_configured ? `modelo: ${state.config.model}` : "modelo sin configurar";
  $("model-status").title = state.config.llm_configured ? "El modelo está configurado" : "Definí LLM_MODEL y LLM_API_KEY u OPENAI_API_KEY";
  const previous = localStorage.getItem("ccm-current-session");
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
