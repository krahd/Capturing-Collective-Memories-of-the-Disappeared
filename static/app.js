const state = {
  session: null,
  selected: new Set(),
  config: { llm_configured: false, audio_ready: false },
  recorder: null,
  recorderStream: null,
  recorderChunks: [],
  currentAudio: null,
  currentAudioUrl: null,
};

const $ = (id) => document.getElementById(id);

async function api(url, options = {}) {
  const isFormData = options.body instanceof FormData;
  const headers = isFormData
    ? { ...(options.headers || {}) }
    : { "Content-Type": "application/json", ...(options.headers || {}) };
  const response = await fetch(url, { headers, ...options });
  const contentType = response.headers.get("content-type") || "";
  const data = contentType.includes("application/json")
    ? await response.json()
    : await response.text();
  if (!response.ok) {
    const message = data?.detail || data?.error || (typeof data === "string" ? data : `HTTP ${response.status}`);
    const error = new Error(message);
    error.payload = data;
    throw error;
  }
  return data;
}

async function audioApi(url, options = {}) {
  const response = await fetch(url, {
    headers: { "Content-Type": "application/json", ...(options.headers || {}) },
    ...options,
  });
  if (!response.ok) {
    let message = `HTTP ${response.status}`;
    try {
      const data = await response.json();
      message = data?.detail || data?.error || message;
    } catch (_) {
      // Keep the HTTP status when the speech service did not return JSON.
    }
    throw new Error(message);
  }
  return response.blob();
}

function selectedTurnIds() {
  return [...state.selected];
}

function setSession(session) {
  state.session = session;
  if (session?.id) localStorage.setItem("ccm-current-session", session.id);
  const existing = new Set(session.turns.map((turn) => turn.id));
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
  $("mic").disabled = !ready || !state.config.audio_ready || !navigator.mediaDevices?.getUserMedia;
  $("speak-replies").disabled = !state.config.audio_ready;
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
  $("selection-summary").textContent = ids.length
    ? `${ids.length} turno${ids.length === 1 ? "" : "s"} seleccionado${ids.length === 1 ? "" : "s"}.`
    : "No hay turnos seleccionados.";
  if (!state.session) return;

  $("annotations").innerHTML = state.session.annotations.map((annotation) => `
    <div class="card"><strong>${escapeHtml(annotation.label)}</strong><div>${escapeHtml(annotation.note || "—")}</div><div class="refs">${annotation.source_turn_ids.map(escapeHtml).join(", ")}</div></div>
  `).join("");

  $("derived-items").innerHTML = state.session.derived_items.map((item) => `
    <div class="card" data-derived-id="${item.id}">
      <strong>${escapeHtml(item.kind)} · ${escapeHtml(item.status)}</strong>
      <textarea class="derived-edit-text" rows="3">${escapeHtml(item.text)}</textarea>
      <select class="derived-edit-status">
        ${["provisional", "reviewed", "disputed", "withdrawn"].map((status) => `<option value="${status}" ${status === item.status ? "selected" : ""}>${status}</option>`).join("")}
      </select>
      <input class="derived-edit-note" value="${escapeHtml(item.note || "")}" placeholder="Nota" />
      <div class="row-actions">
        <button class="save-derived">Guardar cambios</button>
        <button class="delete-derived">Eliminar</button>
      </div>
      <div class="refs">fuentes: ${item.source_turn_ids.map(escapeHtml).join(", ")}</div>
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

  document.querySelectorAll(".delete-derived").forEach((button) => {
    button.addEventListener("click", async () => {
      const card = button.closest(".card");
      const id = card.dataset.derivedId;
      if (!confirm("¿Eliminar este material derivado provisional? La transcripción no se modifica.")) return;
      await mutate(`/api/sessions/${state.session.id}/derived/${id}`, { method: "DELETE" });
    });
  });

  const relationOptions = [
    ...state.session.turns.map((turn) => ({ id: turn.id, label: `${turn.role === "user" ? "turno participante" : "turno sistema"}: ${short(turn.text)}` })),
    ...state.session.derived_items.map((item) => ({ id: item.id, label: `${item.kind}: ${short(item.text)}` })),
  ];
  [$("relation-source"), $("relation-target")].forEach((select) => {
    select.innerHTML = relationOptions.map((option) => `<option value="${option.id}">${escapeHtml(option.label)}</option>`).join("");
  });
  $("add-relation").disabled = relationOptions.length < 2;
  $("relations").innerHTML = state.session.relations.map((relation) => `
    <div class="card"><strong>${escapeHtml(relation.relation_type)}</strong><div>${escapeHtml(relation.source_id)} → ${escapeHtml(relation.target_id)}</div><div>${escapeHtml(relation.note || "")}</div></div>
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

function stopPlayback() {
  if (state.currentAudio) {
    state.currentAudio.pause();
    state.currentAudio.src = "";
    state.currentAudio = null;
  }
  if (state.currentAudioUrl) {
    URL.revokeObjectURL(state.currentAudioUrl);
    state.currentAudioUrl = null;
  }
}

async function speak(text) {
  if (!state.config.audio_ready || !$("speak-replies").checked || !text?.trim()) return;
  stopPlayback();
  $("send-status").textContent = "Preparando voz…";
  try {
    const blob = await audioApi("/api/audio/speech", {
      method: "POST",
      body: JSON.stringify({ text }),
    });
    const url = URL.createObjectURL(blob);
    const audio = new Audio(url);
    state.currentAudio = audio;
    state.currentAudioUrl = url;
    audio.addEventListener("ended", stopPlayback, { once: true });
    await audio.play();
  } catch (error) {
    $("send-status").textContent = `No se pudo reproducir la voz: ${error.message}`;
  } finally {
    if (!state.currentAudio) $("send-status").textContent = "";
  }
}

function preferredRecordingType() {
  const candidates = ["audio/webm;codecs=opus", "audio/ogg;codecs=opus", "audio/webm", "audio/ogg"];
  return candidates.find((type) => window.MediaRecorder?.isTypeSupported?.(type)) || "";
}

function recordingFilename(type) {
  return type.includes("ogg") ? "speech.ogg" : "speech.webm";
}

async function transcribeRecording(blob) {
  $("transcription-status").textContent = "Transcribiendo…";
  const form = new FormData();
  form.append("file", blob, recordingFilename(blob.type));
  try {
    const result = await api("/api/audio/transcribe", { method: "POST", body: form });
    $("message").value = result.text;
    $("transcription-status").textContent = "Transcripción automática: revisala o corregila antes de enviar.";
    $("message").focus();
  } catch (error) {
    $("transcription-status").textContent = `No se pudo transcribir: ${error.message}`;
  }
}

async function startRecording() {
  if (!navigator.mediaDevices?.getUserMedia || state.recorder) return;
  stopPlayback();
  $("transcription-status").textContent = "Escuchando…";
  try {
    const stream = await navigator.mediaDevices.getUserMedia({ audio: true });
    const mimeType = preferredRecordingType();
    const recorder = mimeType ? new MediaRecorder(stream, { mimeType }) : new MediaRecorder(stream);
    state.recorder = recorder;
    state.recorderStream = stream;
    state.recorderChunks = [];
    recorder.addEventListener("dataavailable", (event) => {
      if (event.data.size > 0) state.recorderChunks.push(event.data);
    });
    recorder.addEventListener("stop", async () => {
      const type = recorder.mimeType || state.recorderChunks[0]?.type || "audio/webm";
      const blob = new Blob(state.recorderChunks, { type });
      state.recorder = null;
      state.recorderChunks = [];
      state.recorderStream?.getTracks().forEach((track) => track.stop());
      state.recorderStream = null;
      $("mic").textContent = "Hablar";
      render();
      if (blob.size > 0) await transcribeRecording(blob);
    }, { once: true });
    recorder.start();
    $("mic").textContent = "Terminar";
  } catch (error) {
    state.recorder = null;
    state.recorderStream = null;
    $("transcription-status").textContent = `No se pudo usar el micrófono: ${error.message}`;
  }
}

function stopRecording() {
  if (state.recorder?.state === "recording") state.recorder.stop();
}

$("mic").addEventListener("click", async () => {
  if (state.recorder) stopRecording();
  else await startRecording();
});

$("new-session").addEventListener("click", async () => {
  stopPlayback();
  state.selected.clear();
  const session = await api("/api/sessions", { method: "POST", body: JSON.stringify({}) });
  setSession(session);
  $("message").focus();
  const opening = session.turns.find((turn) => turn.role === "assistant")?.text;
  if (opening) void speak(opening);
});

$("composer").addEventListener("submit", async (event) => {
  event.preventDefault();
  if (!state.session || !state.config.llm_configured) return;
  const text = $("message").value;
  if (!text.trim()) return;
  stopPlayback();
  $("message").value = "";
  $("transcription-status").textContent = "";
  $("send").disabled = true;
  $("send-status").textContent = "Pensando…";
  try {
    const result = await api(`/api/sessions/${state.session.id}/turns`, {
      method: "POST",
      body: JSON.stringify({ text }),
    });
    setSession(result.session);
    $("send-status").textContent = "";
    void speak(result.assistant_turn.text);
  } catch (error) {
    if (error.payload?.session) setSession(error.payload.session);
    $("send-status").textContent = `No se pudo generar respuesta: ${error.message}`;
  } finally {
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
    document.querySelectorAll(".tab").forEach((item) => item.classList.toggle("active", item === tab));
    document.querySelectorAll(".tab-panel").forEach((panel) => panel.classList.toggle("active", panel.id === `tab-${tab.dataset.tab}`));
  });
});

async function init() {
  state.config = await api("/api/config");
  if (state.config.llm_configured) {
    const provider = state.config.llm?.provider ? `${state.config.llm.provider} · ` : "";
    $("model-status").textContent = `${provider}${state.config.model}`;
    $("model-status").title = `perfil local: ${state.config.llm?.profile || "auto"}`;
  } else {
    $("model-status").textContent = "modelo local no disponible";
    $("model-status").title = state.config.llm?.reason || "Iniciá Ollama u oMLX y descargá el modelo configurado.";
  }

  if (state.config.audio_ready) {
    $("speech-status").textContent = "voz local";
    $("speech-status").title = `STT: ${state.config.audio?.stt_model}\nTTS: ${state.config.audio?.tts_model}`;
  } else {
    $("speech-status").textContent = "voz local no disponible";
    $("speech-status").title = state.config.audio?.reason || "Iniciá MLX-Audio en el puerto configurado.";
  }

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

window.addEventListener("beforeunload", () => {
  stopPlayback();
  state.recorderStream?.getTracks().forEach((track) => track.stop());
});

init().catch((error) => {
  $("model-status").textContent = "error de inicio";
  console.error(error);
});
