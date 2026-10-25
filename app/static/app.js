const state = { caseId: null, tab: "handoff", audit: null, arc: 1, busy: false };

function esc(value) {
  return String(value ?? "").replace(/[&<>\"']/g, (c) => ({
    "&": "&amp;", "<": "&lt;", ">": "&gt;", '"': "&quot;", "'": "&#39;"
  }[c]));
}

async function api(path, opts) {
  opts = opts || {};
  opts.headers = { ...(opts.headers || {}) };
  const key = window.localStorage.getItem("supportforge_api_key");
  if (key) opts.headers["x-api-key"] = key;
  const user = window.localStorage.getItem("supportforge_user");
  if (user) opts.headers["x-supportforge-user"] = user;
  const res = await fetch(path, {
    ...opts,
    signal: AbortSignal.timeout((opts && opts.timeout) || 180000),
  });
  if (!res.ok) throw new Error(await res.text());
  const ct = res.headers.get("content-type") || "";
  if (ct.includes("application/json")) return res.json();
  return res.text();
}

function $(id) { return document.getElementById(id); }

function toast(msg) {
  const el = $("toast");
  el.textContent = msg;
  el.classList.remove("hidden");
  clearTimeout(toast._t);
  toast._t = setTimeout(() => el.classList.add("hidden"), 3200);
}

function setArc(n) {
  state.arc = n;
  document.querySelectorAll(".arc-step").forEach((el) => {
    const s = Number(el.dataset.step);
    el.classList.toggle("active", s === n);
    el.classList.toggle("done", s < n);
  });
}

async function refreshHealth() {
  try {
    const h = await api("/api/health", { timeout: 5000 });
    const el = $("health");
    el.textContent = h.ok ? "console · online" : "degraded";
    el.classList.toggle("ok", !!h.ok);
    const p = h.provider || {};
    const mp = $("model-pill");
    if (h.model_online) {
      mp.textContent = `${p.provider} · ${p.model}`;
      mp.classList.add("live");
      $("agent-tag").textContent = `Live model · ${p.provider} / ${p.model}`;
    } else if (p.provider === "ollama" && p.status === "no_models") {
      mp.textContent = "ollama · pulling model…";
      mp.classList.remove("live");
      $("agent-tag").textContent = "Ollama up — waiting for model pull";
    } else {
      mp.textContent = "model offline";
      mp.classList.remove("live");
      $("agent-tag").textContent = "Start Ollama + pull qwen2.5:7b-instruct";
    }
  } catch {
    $("health").textContent = "offline";
    $("health").classList.remove("ok");
    $("model-pill").textContent = "model ?";
  }
}

async function loadCases() {
  const cases = await api("/api/cases");
  const ul = $("case-list");
  ul.innerHTML = "";
  cases.forEach((c) => {
    const li = document.createElement("li");
    li.dataset.id = c.id;
    if (c.id === state.caseId) li.classList.add("active");
    li.innerHTML = `<div class="id">${esc(c.id)}</div>
      <div class="meta">${esc(c.completeness == null ? "not audited" : c.completeness + "% complete")} · ${esc(c.files)} files</div>`;
    li.onclick = () => selectCase(c.id);
    ul.appendChild(li);
  });
  if (!state.caseId && cases.length) selectCase(cases[0].id);
}

async function selectCase(id) {
  state.caseId = id;
  $("case-title").textContent = id;
  $("btn-audit").disabled = false;
  document.querySelectorAll("#case-list li").forEach((li) => {
    li.classList.toggle("active", li.dataset.id === id);
  });
  const detail = await api(`/api/cases/${id}`);
  renderFiles(detail.files || []);
  if (detail.audit) {
    renderAudit(detail.audit);
    const pct = detail.audit.completeness_percent || 0;
    if (pct < 60) setArc(2);
    else if (pct >= 100) setArc(Math.max(state.arc, 3));
  } else {
    $("meter").classList.add("hidden");
    $("evidence").innerHTML = '<div class="empty">No audit yet. Run evidence audit.</div>';
    $("hypotheses").innerHTML = "";
    $("doc").textContent = "Run an audit or Investigate with model.";
  }
  await loadDoc();
}

function renderFiles(files) {
  const ul = $("files");
  ul.innerHTML = files.map((f) => `<li>${esc(f)}</li>`).join("") || "<li class='empty'>No files</li>";
}

function renderAudit(audit) {
  state.audit = audit;
  $("meter").classList.remove("hidden");
  const pct = audit.completeness_percent || 0;
  $("meter-fill").style.width = `${pct}%`;
  $("meter-pct").textContent = `${pct}%`;
  $("event-count").textContent = String((audit.timeline || []).length);
  const rows = (audit.evidence || [])
    .filter((e) => e.required)
    .map(
      (e) => `<tr>
        <td>${esc(e.item)}</td>
        <td><span class="badge ${esc(e.status)}">${esc(e.status)}</span></td>
        <td>${esc((e.paths || []).join(", ") || "—")}</td>
      </tr>`
    )
    .join("");
  $("evidence").innerHTML = `<table class="evidence-table">
    <thead><tr><th>Item</th><th>Status</th><th>Path</th></tr></thead>
    <tbody>${rows}</tbody></table>`;
  $("hypotheses").innerHTML = (audit.hypotheses || []).map((h) => `<li>${esc(h)}</li>`).join("");
  const flags = audit.security_flags || [];
  if (flags.length) {
    $("evidence").insertAdjacentHTML(
      "beforeend",
      `<div class="empty" style="color:var(--warn)">Security: ${esc(flags.join("; "))} (treated as untrusted data)</div>`
    );
  }
}

async function loadDoc() {
  if (!state.caseId) return;
  try {
    if (state.tab === "timeline") {
      const a = state.audit || (await api(`/api/cases/${state.caseId}`)).audit;
      const events = (a && a.timeline) || [];
      $("doc").textContent = events.length
        ? events.map((e) => `${e.time}  [${e.severity}]  ${e.summary}\n  ↑ ${e.citation}`).join("\n\n")
        : "No timeline events yet.";
      return;
    }
    if (state.tab === "llm") {
      try {
        $("doc").textContent = await api(`/api/cases/${state.caseId}/llm-report`);
      } catch {
        $("doc").textContent = "No LLM report yet. Click «Investigate with model».";
      }
      return;
    }
    const map = { handoff: "handoff", requests: "requests" };
    $("doc").textContent = await api(`/api/cases/${state.caseId}/${map[state.tab]}`);
  } catch {
    $("doc").textContent = `No ${state.tab} yet. Run audit first.`;
  }
}

async function runAudit() {
  if (!state.caseId) return;
  $("btn-audit").disabled = true;
  try {
    const audit = await api(`/api/cases/${state.caseId}/audit`, { method: "POST" });
    renderAudit(audit);
    setArc(audit.completeness_percent < 60 ? 2 : 3);
    await loadCases();
    await loadDoc();
    toast(`Audit ${state.caseId}: ${audit.completeness_percent}%`);
  } catch (e) {
    showError(e);
  } finally {
    $("btn-audit").disabled = false;
  }
}

function showError(err) {
  const msg = (err && err.message) || String(err);
  const tip =
    msg.includes("Failed to fetch") || msg.includes("Load failed") || msg.includes("NetworkError")
      ? "\n\nServer offline. Run: bash ~/Desktop/Nvidia/project/scripts/start-console.sh"
      : "";
  $("doc").textContent = `Error: ${msg}${tip}`;
  $("health").textContent = "offline";
  $("health").classList.remove("ok");
}

async function resetDemo() {
  try {
    const audit = await api("/api/demo/reset?case_id=CASE-1042", { method: "POST" });
    setArc(1);
    await loadCases();
    await selectCase("CASE-1042");
    renderAudit(audit);
    setArc(2);
    await loadDoc();
    await refreshHealth();
    toast("Demo reset → incomplete pack");
  } catch (e) {
    showError(e);
  }
}

async function injectComplete() {
  try {
    const audit = await api("/api/demo/inject-complete?case_id=CASE-1042", { method: "POST" });
    await loadCases();
    await selectCase("CASE-1042");
    renderAudit(audit);
    setArc(3);
    await loadDoc();
    await refreshHealth();
    toast("Evidence injected · 100% complete");
  } catch (e) {
    showError(e);
  }
}

async function investigateCase() {
  const id = state.caseId || "CASE-1042";
  await sendChat(`Investigate ${id}`);
}

function addBubble(role, text) {
  const log = $("chat-log");
  const div = document.createElement("div");
  div.className = `bubble ${role}`;
  div.textContent = text;
  log.appendChild(div);
  log.scrollTop = log.scrollHeight;
  return div;
}

async function sendChat(message) {
  const msg = (message || "").trim();
  if (!msg || state.busy) return;
  state.busy = true;
  $("btn-send").classList.add("busy");
  $("btn-investigate").classList.add("busy");
  addBubble("user", msg);
  $("chat-input").value = "";
  const thinking = addBubble("thinking", "Model reasoning over case files…");
  try {
    const data = await api("/api/chat", {
      method: "POST",
      headers: { "content-type": "application/json" },
      body: JSON.stringify({ message: msg }),
      timeout: 200000,
    });
    thinking.remove();
    addBubble("agent", data.reply || "(no reply)");
    if (data.model_meta) {
      setArc(4);
      state.tab = "llm";
      document.querySelectorAll(".tab").forEach((t) => {
        t.classList.toggle("active", t.dataset.tab === "llm");
      });
      toast(`LLM · ${data.model_meta.provider} / ${data.model_meta.model}`);
    } else if (msg.toLowerCase().includes("inject")) {
      setArc(3);
    } else if (msg.toLowerCase().includes("audit") || msg.toLowerCase().includes("reset")) {
      setArc(2);
    }
    if (data.case_id) {
      await loadCases();
      await selectCase(data.case_id);
      if (data.audit) renderAudit(data.audit);
      await loadDoc();
    }
    await refreshHealth();
  } catch (e) {
    thinking.remove();
    addBubble("agent", `Error: ${(e && e.message) || e}`);
    showError(e);
  } finally {
    state.busy = false;
    $("btn-send").classList.remove("busy");
    $("btn-investigate").classList.remove("busy");
  }
}

function wire() {
  $("btn-refresh").onclick = loadCases;
  $("btn-audit").onclick = runAudit;
  $("btn-reset").onclick = resetDemo;
  $("btn-inject").onclick = injectComplete;
  $("btn-investigate").onclick = investigateCase;
  document.querySelectorAll(".tab").forEach((tab) => {
    tab.onclick = () => {
      document.querySelectorAll(".tab").forEach((t) => t.classList.remove("active"));
      tab.classList.add("active");
      state.tab = tab.dataset.tab;
      loadDoc();
    };
  });
  $("chat-form").onsubmit = (ev) => {
    ev.preventDefault();
    sendChat($("chat-input").value);
  };
  document.querySelectorAll(".chip").forEach((chip) => {
    chip.onclick = () => sendChat(chip.dataset.msg);
  });
}

wire();
setArc(1);
refreshHealth();
loadCases();
addBubble(
  "agent",
  "SupportForge ready.\n1) Reset demo → 2) Audit gaps → 3) Inject evidence → 4) Investigate with model."
);
setInterval(refreshHealth, 6000);
