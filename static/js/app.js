"use strict";

const $ = (s) => document.querySelector(s);
const $$ = (s) => document.querySelectorAll(s);

const state = {
  rtype: "model",
  repo: null,          // current open repo info
  revision: "",
  selected: new Set(), // selected file paths
};

// ---------- helpers ----------
function fmtBytes(n) {
  if (!n) return "0 B";
  const u = ["B", "KB", "MB", "GB", "TB"];
  let i = 0;
  while (n >= 1024 && i < u.length - 1) { n /= 1024; i++; }
  return `${n.toFixed(i ? 1 : 0)} ${u[i]}`;
}
function fmtNum(n) {
  if (n >= 1e6) return (n / 1e6).toFixed(1) + "M";
  if (n >= 1e3) return (n / 1e3).toFixed(1) + "k";
  return String(n || 0);
}
function fmtEta(s) {
  if (!s || s <= 0) return "–";
  s = Math.round(s);
  if (s < 60) return s + "s";
  if (s < 3600) return Math.floor(s / 60) + "m " + (s % 60) + "s";
  return Math.floor(s / 3600) + "h " + Math.floor((s % 3600) / 60) + "m";
}
let toastTimer;
function toast(msg, isErr) {
  const t = $("#toast");
  t.textContent = msg;
  t.classList.remove("hidden", "err");
  if (isErr) t.classList.add("err");
  clearTimeout(toastTimer);
  toastTimer = setTimeout(() => t.classList.add("hidden"), 3200);
}
async function jget(url) {
  const r = await fetch(url);
  const d = await r.json();
  if (!r.ok) throw new Error(d.error || r.statusText);
  return d;
}
async function jsend(url, method, body) {
  const r = await fetch(url, {
    method,
    headers: { "Content-Type": "application/json" },
    body: body ? JSON.stringify(body) : undefined,
  });
  const d = await r.json();
  if (!r.ok) throw new Error(d.error || r.statusText);
  return d;
}

// ---------- tabs ----------
$$(".tab").forEach((b) =>
  b.addEventListener("click", () => {
    $$(".tab").forEach((x) => x.classList.remove("active"));
    $$(".panel").forEach((x) => x.classList.remove("active"));
    b.classList.add("active");
    $("#" + b.dataset.tab).classList.add("active");
    if (b.dataset.tab === "history") loadHistory();
    if (b.dataset.tab === "settings") loadSettings();
  })
);

// ---------- theme ----------
$("#themeToggle").addEventListener("click", async () => {
  const cur = document.documentElement.getAttribute("data-theme");
  const next = cur === "dark" ? "light" : "dark";
  document.documentElement.setAttribute("data-theme", next);
  try { await jsend("/api/settings", "POST", { theme: next }); } catch {}
});

// ---------- search ----------
$$(".seg-btn").forEach((b) =>
  b.addEventListener("click", () => {
    $$(".seg-btn").forEach((x) => x.classList.remove("active"));
    b.classList.add("active");
    state.rtype = b.dataset.rtype;
  })
);
$("#searchBtn").addEventListener("click", doSearch);
$("#searchInput").addEventListener("keydown", (e) => { if (e.key === "Enter") doSearch(); });

async function doSearch() {
  const q = $("#searchInput").value.trim();
  const sort = $("#sortSelect").value;
  const box = $("#results");
  box.innerHTML = '<div class="spinner">Searching…</div>';
  try {
    const d = await jget(`/api/search?q=${encodeURIComponent(q)}&type=${state.rtype}&sort=${sort}&limit=40`);
    if (!d.results.length) { box.innerHTML = '<div class="empty">No results.</div>'; return; }
    box.innerHTML = "";
    d.results.forEach((it) => box.appendChild(resultCard(it)));
  } catch (e) {
    box.innerHTML = `<div class="empty">Error: ${e.message}</div>`;
  }
}

function resultCard(it) {
  const el = document.createElement("div");
  el.className = "card";
  const pipe = it.pipeline_tag ? `<span class="tag pipe">${it.pipeline_tag}</span>` : "";
  const tags = (it.tags || []).slice(0, 5).map((t) => `<span class="tag">${t}</span>`).join("");
  el.innerHTML = `
    <h3>${it.id}</h3>
    <div class="stats">
      <span>⬇ ${fmtNum(it.downloads)}</span>
      <span>❤ ${fmtNum(it.likes)}</span>
      <span>${it.type}</span>
    </div>
    <div>${pipe}${tags}</div>`;
  el.addEventListener("click", () => openRepo(it.id, it.type, ""));
  return el;
}

// ---------- quick open ----------
$("#openBtn").addEventListener("click", () => {
  const id = $("#directRepo").value.trim();
  if (!id) return;
  openRepo(id, state.rtype, $("#directRev").value.trim());
});

// ---------- repo modal ----------
async function openRepo(id, type, revision) {
  const modal = $("#repoModal");
  modal.classList.remove("hidden");
  $("#repoTitle").textContent = id;
  $("#repoMeta").textContent = "Loading…";
  $("#fileList").innerHTML = '<div class="spinner">Loading files…</div>';
  $("#readmeContent").textContent = "";
  state.selected.clear();
  try {
    const info = await jget(`/api/repo?id=${encodeURIComponent(id)}&type=${type}&revision=${encodeURIComponent(revision || "")}`);
    state.repo = info;
    state.revision = revision || (info.branches[0] || "main");
    renderRepo(info);
  } catch (e) {
    $("#fileList").innerHTML = `<div class="empty">Error: ${e.message}</div>`;
    $("#repoMeta").textContent = "";
  }
}

function renderRepo(info) {
  const pipe = info.pipeline_tag ? `· ${info.pipeline_tag}` : "";
  $("#repoMeta").innerHTML =
    `⬇ ${fmtNum(info.downloads)} · ❤ ${fmtNum(info.likes)} · ${info.files.length} files · ${fmtBytes(info.total_size)} ${pipe}`;
  const rev = $("#revisionSelect");
  rev.innerHTML = "";
  (info.branches.length ? info.branches : ["main"]).forEach((b) => {
    const o = document.createElement("option");
    o.value = b; o.textContent = b;
    if (b === state.revision) o.selected = true;
    rev.appendChild(o);
  });
  $("#readmeContent").textContent = info.readme || "(no README)";
  $("#fileFilter").value = "";
  $("#selectAll").checked = false;
  renderFiles();
}

$("#revisionSelect").addEventListener("change", (e) => {
  openRepo(state.repo.id, state.repo.type, e.target.value);
});
$("#fileFilter").addEventListener("input", renderFiles);
$("#selectAll").addEventListener("change", (e) => {
  const visible = filteredFiles();
  if (e.target.checked) visible.forEach((f) => state.selected.add(f.path));
  else visible.forEach((f) => state.selected.delete(f.path));
  renderFiles();
});

function filteredFiles() {
  const q = $("#fileFilter").value.trim().toLowerCase();
  if (!q) return state.repo.files;
  return state.repo.files.filter((f) => f.path.toLowerCase().includes(q));
}

function renderFiles() {
  const list = $("#fileList");
  const files = filteredFiles();
  list.innerHTML = "";
  files.forEach((f) => {
    const row = document.createElement("div");
    row.className = "file-row";
    const checked = state.selected.has(f.path) ? "checked" : "";
    row.innerHTML = `
      <input type="checkbox" data-path="${encodeURIComponent(f.path)}" ${checked} />
      <span class="fname">${f.path}</span>
      <span class="fsize">${fmtBytes(f.size)}</span>`;
    row.querySelector("input").addEventListener("change", (e) => {
      const p = decodeURIComponent(e.target.dataset.path);
      if (e.target.checked) state.selected.add(p); else state.selected.delete(p);
      updateSelSummary();
    });
    list.appendChild(row);
  });
  updateSelSummary();
}

function updateSelSummary() {
  const sel = state.repo.files.filter((f) => state.selected.has(f.path));
  const bytes = sel.reduce((a, f) => a + (f.size || 0), 0);
  $("#selSummary").textContent = `${sel.length} selected · ${fmtBytes(bytes)}`;
}

$("#closeModal").addEventListener("click", () => $("#repoModal").classList.add("hidden"));
$("#repoModal").addEventListener("click", (e) => { if (e.target.id === "repoModal") $("#repoModal").classList.add("hidden"); });

$("#downloadSelected").addEventListener("click", async () => {
  const files = state.repo.files.filter((f) => state.selected.has(f.path));
  if (!files.length) { toast("Select at least one file.", true); return; }
  try {
    await jsend("/api/download", "POST", {
      repo_id: state.repo.id,
      repo_type: state.repo.type,
      revision: state.revision,
      files: files.map((f) => ({ path: f.path, size: f.size, url: f.url })),
    });
    toast(`Queued ${files.length} file(s) from ${state.repo.id}`);
    $("#repoModal").classList.add("hidden");
    document.querySelector('.tab[data-tab="queue"]').click();
  } catch (e) {
    toast(e.message, true);
  }
});

// ---------- queue (SSE) ----------
function renderQueue(tasks) {
  $("#queueBadge").textContent = tasks.filter((t) => ["queued", "downloading"].includes(t.status)).length;
  const list = $("#queueList");
  if (!tasks.length) { list.innerHTML = '<div class="empty">Queue is empty.</div>'; return; }
  list.innerHTML = "";
  tasks.forEach((t) => list.appendChild(queueItem(t)));
}

function queueItem(t) {
  const el = document.createElement("div");
  el.className = "qitem";
  const active = t.status === "downloading" || t.status === "queued";
  const speed = t.speed > 0 ? `${fmtBytes(t.speed)}/s` : "";
  el.innerHTML = `
    <div class="qitem-head">
      <span class="qid">${t.repo_id} <small style="color:var(--muted)">@${t.revision}</small></span>
      <span class="qstatus ${t.status}">${t.status}</span>
    </div>
    <div class="progress"><div style="width:${t.percent}%"></div></div>
    <div class="qmeta">
      <span>${fmtBytes(t.done_bytes)} / ${fmtBytes(t.total_bytes)} (${t.percent}%)</span>
      <span>${t.current_file || ""}</span>
      <span>${speed} ${active && t.speed > 0 ? "· ETA " + fmtEta(t.eta) : ""}</span>
    </div>
    ${t.error ? `<div class="qmeta" style="color:var(--red)">${t.error}</div>` : ""}
    <div class="qactions"></div>`;
  const actions = el.querySelector(".qactions");
  if (active) {
    const b = document.createElement("button");
    b.className = "danger"; b.textContent = "Cancel";
    b.onclick = () => jsend(`/api/download/${t.id}/cancel`, "POST").catch((e) => toast(e.message, true));
    actions.appendChild(b);
  } else {
    const b = document.createElement("button");
    b.className = "mini"; b.textContent = "Remove";
    b.onclick = () => jsend(`/api/download/${t.id}`, "DELETE").catch((e) => toast(e.message, true));
    actions.appendChild(b);
    if (t.status === "completed") {
      const open = document.createElement("span");
      open.className = "sel-summary"; open.style.marginLeft = "8px";
      open.textContent = `Saved ${t.file_count} file(s)`;
      actions.appendChild(open);
    }
  }
  return el;
}

function startStream() {
  const es = new EventSource("/api/stream");
  es.onmessage = (e) => {
    try { renderQueue(JSON.parse(e.data).tasks); } catch {}
  };
  es.onerror = () => { es.close(); setTimeout(startStream, 3000); };
}

// ---------- history ----------
async function loadHistory() {
  const list = $("#historyList");
  list.innerHTML = '<div class="spinner">Loading…</div>';
  try {
    const d = await jget("/api/history");
    if (!d.history.length) { list.innerHTML = '<div class="empty">No history yet.</div>'; return; }
    list.innerHTML = "";
    d.history.forEach((h) => {
      const el = document.createElement("div");
      el.className = "qitem";
      const date = new Date(h.time * 1000).toLocaleString();
      el.innerHTML = `
        <div class="qitem-head">
          <span class="qid">${h.repo_id} <small style="color:var(--muted)">@${h.revision}</small></span>
          <span class="qstatus completed">${h.repo_type}</span>
        </div>
        <div class="qmeta">
          <span>${h.files} file(s) · ${fmtBytes(h.bytes)}</span>
          <span>${date}</span>
        </div>
        <div class="qmeta"><span style="word-break:break-all">${h.dest}</span></div>`;
      list.appendChild(el);
    });
  } catch (e) {
    list.innerHTML = `<div class="empty">Error: ${e.message}</div>`;
  }
}
$("#clearHistory").addEventListener("click", async () => {
  await jsend("/api/history", "DELETE");
  loadHistory();
});

// ---------- settings ----------
async function loadSettings() {
  try {
    const s = await jget("/api/settings");
    $("#downloadDir").value = s.download_dir || "";
    $("#maxWorkers").value = s.max_workers || 3;
    $("#tokenInput").value = "";
    const st = $("#tokenStatus");
    st.textContent = s.token_set ? "Token set" : "No token";
    st.className = "pill" + (s.token_set ? " set" : "");
    loadDisk();
  } catch (e) { toast(e.message, true); }
}
async function loadDisk() {
  try {
    const d = await jget("/api/disk");
    if (d.error) { $("#diskInfo").textContent = ""; return; }
    const pct = ((d.used / d.total) * 100).toFixed(0);
    $("#diskInfo").textContent = `Disk: ${fmtBytes(d.free)} free of ${fmtBytes(d.total)} (${pct}% used)`;
  } catch { $("#diskInfo").textContent = ""; }
}
$("#saveSettings").addEventListener("click", async () => {
  const body = {
    download_dir: $("#downloadDir").value.trim(),
    max_workers: parseInt($("#maxWorkers").value, 10) || 3,
  };
  const tok = $("#tokenInput").value.trim();
  if (tok) body.token = tok;
  try {
    await jsend("/api/settings", "POST", body);
    const m = $("#settingsSaved");
    m.textContent = "Saved ✓ (worker count applies on restart)";
    setTimeout(() => (m.textContent = ""), 3000);
    loadSettings();
  } catch (e) { toast(e.message, true); }
});

// ---------- init ----------
startStream();
doSearch();
