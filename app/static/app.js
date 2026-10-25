const state = { caseId: null, tab: "handoff", audit: null };

async function api(path, opts) {
  const res = await fetch(path, opts);
  if (!res.ok) throw new Error(await res.text());
  const ct = res.headers.get("content-type") || "";
  if (ct.includes("application/json")) return res.json();
  return res.text();
}

function $(id) { return document.getElementById(id); }

async function refreshHealth() {
  try {
    const h = await api("/api/health");
    const el = $("health");
    el.textContent = h.ok ? "local · online" : "degraded";
    el.classList.toggle("ok", !!h.ok);
  } catch {
    $("health").textContent = "offline";
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
    li.innerHTML = `<div class="id">${c.id}</div>
      <div class="meta">${c.completeness == null ? "not audited" : c.completeness + "% complete"} · ${c.files} files</div>`;
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
  if (detail.audit) renderAudit(detail.audit);
  else {
    $("meter").classList.add("hidden");
    $("evidence").innerHTML = '<div class="empty">No audit yet. Run evidence audit.</div>';
    $("hypotheses").innerHTML = "";
    $("doc").textContent = "Run an audit to generate the engineering package.";
  }
  await loadDoc();
}

function renderFiles(files) {
  const ul = $("files");
  ul.innerHTML = files.map((f) => `<li>${f}</li>`).join("") || "<li class='empty'>No files</li>";
}

function renderAudit(audit) {
  state.audit = audit;
  $("meter").classList.remove("hidden");
  const pct = audit.completeness_percent || 0;
  $("meter-fill").style.width = `${pct}%`;
  $("meter-pct").textContent = `${pct}%`;
  const rows = (audit.evidence || [])
    .filter((e) => e.required)
    .map(
      (e) => `<tr>
        <td>${e.item}</td>
        <td><span class="badge ${e.status}">${e.status}</span></td>
        <td>${(e.paths || []).join(", ") || "—"}</td>
      </tr>`
    )
    .join("");
  $("evidence").innerHTML = `<table class="evidence-table">
    <thead><tr><th>Item</th><th>Status</th><th>Path</th></tr></thead>
    <tbody>${rows}</tbody></table>`;
  $("hypotheses").innerHTML = (audit.hypotheses || []).map((h) => `<li>${h}</li>`).join("");
}

async function loadDoc() {
  if (!state.caseId) return;
  const map = { handoff: "handoff", requests: "requests", timeline: "timeline" };
  try {
    if (state.tab === "timeline") {
      const a = state.audit || (await api(`/api/cases/${state.caseId}`)).audit;
      const events = (a && a.timeline) || [];
      $("doc").textContent = events.length
        ? events.map((e) => `${e.time}  [${e.severity}]  ${e.summary}\n  ↑ ${e.citation}`).join("\n\n")
        : "No timeline events yet.";
      return;
    }
    const text = await api(`/api/cases/${state.caseId}/${map[state.tab]}`);
    $("doc").textContent = text;
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
    await loadCases();
    await loadDoc();
  } catch (e) {
    alert(e.message || e);
  } finally {
    $("btn-audit").disabled = false;
  }
}

function showError(err) {
  const msg = (err && err.message) || String(err);
  const tip =
    msg.includes("Failed to fetch") || msg.includes("Load failed") || msg.includes("NetworkError")
      ? "\n\nServer is offline. In Terminal run:\nbash ~/Desktop/Nvidia/project/scripts/start-console.sh"
      : "";
  $("doc").textContent = `Error: ${msg}${tip}`;
  $("health").textContent = "offline";
  $("health").classList.remove("ok");
}

async function resetDemo() {
  try {
    const audit = await api("/api/demo/reset?case_id=CASE-1042", { method: "POST" });
    await loadCases();
    await selectCase("CASE-1042");
    renderAudit(audit);
    await loadDoc();
    await refreshHealth();
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
    await loadDoc();
    await refreshHealth();
  } catch (e) {
    showError(e);
  }
}

function addBubble(role, text) {
  const log = $("chat-log");
  const div = document.createElement("div");
  div.className = `bubble ${role}`;
  div.textContent = text;
  log.appendChild(div);
  log.scrollTop = log.scrollHeight;
}

async function sendChat(message) {
  const msg = (message || "").trim();
  if (!msg) return;
  addBubble("user", msg);
  $("chat-input").value = "";
  try {
    const data = await api("/api/chat", {
      method: "POST",
      headers: { "content-type": "application/json" },
      body: JSON.stringify({ message: msg }),
    });
    addBubble("agent", data.reply || "(no reply)");
    if (data.case_id) {
      await loadCases();
      await selectCase(data.case_id);
      if (data.audit) renderAudit(data.audit);
      await loadDoc();
    }
    await refreshHealth();
  } catch (e) {
    addBubble("agent", `Error: ${(e && e.message) || e}`);
    showError(e);
  }
}

function wire() {
  $("btn-refresh").onclick = loadCases;
  $("btn-audit").onclick = runAudit;
  $("btn-reset").onclick = resetDemo;
  $("btn-inject").onclick = injectComplete;
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
refreshHealth();
loadCases();
addBubble(
  "agent",
  "SupportForge laptop mode ready. No GB10 needed for this demo.\nClick the chips below or type a command."
);
setInterval(refreshHealth, 8000);
