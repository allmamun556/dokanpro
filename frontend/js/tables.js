let tables = [];

const STATUS_CYCLE = { free: "occupied", occupied: "reserved", reserved: "free" };
const STATUS_BADGE = { free: "badge-ok", occupied: "badge-low", reserved: "badge-warning" };

async function init() {
  const user = await renderNav("tables.html");
  if (!hasPermission(user, "tables.manage")) {
    document.querySelector(".page").innerHTML = `<div class="empty-state">You do not have permission to manage tables.</div>`;
    return;
  }
  await loadTables();
  document.getElementById("new-table-form").addEventListener("submit", submitNewTable);
}

async function loadTables() {
  try {
    tables = await apiFetch("/reservation-tables");
    render();
  } catch (err) {
    showToast(err.message, "error");
  }
}

function render() {
  const grid = document.getElementById("table-grid");
  const emptyState = document.getElementById("empty-state");

  if (tables.length === 0) {
    grid.innerHTML = "";
    emptyState.style.display = "block";
    return;
  }
  emptyState.style.display = "none";

  grid.innerHTML = tables
    .map(
      (t) => `
      <div class="card">
        <div style="display:flex; justify-content:space-between; align-items:center;">
          <h3 style="margin:0;">${escapeHtml(t.label)}</h3>
          <span class="badge ${STATUS_BADGE[t.status]}" style="cursor:pointer;" onclick="cycleStatus(${t.id}, '${t.status}')" title="Click to change status">${t.status}</span>
        </div>
        <div style="font-size:13px; color:var(--text-muted); margin:8px 0;">Seats ${t.capacity}</div>
        <div style="display:flex; gap:6px; flex-wrap:wrap;">
          <button class="btn btn-secondary btn-sm" onclick="printTableQr(${t.id}, '${escapeHtml(t.label)}')">Print QR</button>
          <a class="btn btn-primary btn-sm" href="pos.html?table_id=${t.id}">New Order</a>
        </div>
      </div>
    `
    )
    .join("");
}

async function cycleStatus(id, currentStatus) {
  const next = STATUS_CYCLE[currentStatus];
  try {
    await apiFetch(`/reservation-tables/${id}`, { method: "PATCH", body: JSON.stringify({ status: next }) });
    await loadTables();
  } catch (err) {
    showToast(err.message, "error");
  }
}

function printTableQr(id, label) {
  const printArea = document.getElementById("print-area");
  printArea.innerHTML = `
    <div style="text-align:center; padding:40px;">
      <h2>${escapeHtml(label)}</h2>
      <div id="qr-code" style="display:inline-block;"></div>
      <p>Scan to order</p>
    </div>
  `;
  const url = `${window.location.origin}/site/dine-in.html?table_id=${id}`;
  new QRCode(document.getElementById("qr-code"), { text: url, width: 260, height: 260 });
  window.print();
}

function openNewTableModal() {
  document.getElementById("new-table-modal").style.display = "flex";
}

function closeNewTableModal() {
  document.getElementById("new-table-modal").style.display = "none";
  document.getElementById("new-table-form").reset();
}

async function submitNewTable(e) {
  e.preventDefault();
  try {
    await apiFetch("/reservation-tables", {
      method: "POST",
      body: JSON.stringify({
        label: document.getElementById("t-label").value.trim(),
        capacity: parseInt(document.getElementById("t-capacity").value, 10),
      }),
    });
    showToast("Table created");
    closeNewTableModal();
    await loadTables();
  } catch (err) {
    showToast(err.message, "error");
  }
}

function escapeHtml(str) {
  const div = document.createElement("div");
  div.textContent = str;
  return div.innerHTML;
}

init();
