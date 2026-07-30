let reservations = [];
let tables = [];

async function init() {
  const user = await renderNav("reservations.html");
  if (!hasPermission(user, "reservations.manage")) {
    document.querySelector(".page").innerHTML = `<div class="empty-state">You do not have permission to manage reservations.</div>`;
    return;
  }

  const dateInput = document.getElementById("date-filter");
  dateInput.value = new Date().toISOString().slice(0, 10);
  dateInput.addEventListener("change", loadReservations);

  tables = await apiFetch("/reservation-tables");
  document.getElementById("rm-table").innerHTML =
    `<option value="">— Unassigned —</option>` +
    tables.map((t) => `<option value="${t.id}">${escapeHtml(t.label)} (seats ${t.capacity})</option>`).join("");

  await loadReservations();
}

async function loadReservations() {
  try {
    const date = document.getElementById("date-filter").value;
    reservations = await apiFetch(`/reservations?date_filter=${date}`);
    render();
  } catch (err) {
    showToast(err.message, "error");
  }
}

function render() {
  const tbody = document.getElementById("reservation-rows");
  const emptyState = document.getElementById("empty-state");

  if (reservations.length === 0) {
    tbody.innerHTML = "";
    emptyState.style.display = "block";
    return;
  }
  emptyState.style.display = "none";

  tbody.innerHTML = reservations
    .map((r) => {
      const table = tables.find((t) => t.id === r.table_id);
      return `
        <tr>
          <td>${new Date(r.reservation_time).toLocaleTimeString([], { hour: "2-digit", minute: "2-digit" })}</td>
          <td>${escapeHtml(r.guest_name)}<br><span style="font-size:12px; color:var(--text-muted);">${escapeHtml(r.guest_phone)}</span></td>
          <td>${r.party_size}</td>
          <td>${table ? escapeHtml(table.label) : "—"}</td>
          <td><span class="badge badge-${statusColor(r.status)}">${r.status}</span></td>
          <td style="font-size:13px; color:var(--text-muted);">${escapeHtml(r.notes || "")}</td>
          <td><button class="btn btn-secondary btn-sm" onclick="openReservationModal(${r.id})">Edit</button></td>
        </tr>
      `;
    })
    .join("");
}

function statusColor(status) {
  if (status === "confirmed" || status === "seated" || status === "completed") return "ok";
  if (status === "cancelled" || status === "no_show") return "low";
  return "warning";
}

function openReservationModal(id) {
  const r = reservations.find((x) => x.id === id);
  document.getElementById("rm-id").textContent = r.id;
  document.getElementById("rm-status").value = r.status;
  document.getElementById("rm-table").value = r.table_id || "";
  document.getElementById("res-modal").dataset.id = r.id;
  document.getElementById("res-modal").style.display = "flex";
}

function closeReservationModal() {
  document.getElementById("res-modal").style.display = "none";
}

async function saveReservation() {
  const id = document.getElementById("res-modal").dataset.id;
  const tableVal = document.getElementById("rm-table").value;
  const payload = {
    status: document.getElementById("rm-status").value,
    table_id: tableVal ? parseInt(tableVal, 10) : null,
  };
  try {
    await apiFetch(`/reservations/${id}`, { method: "PATCH", body: JSON.stringify(payload) });
    showToast("Reservation updated");
    closeReservationModal();
    await loadReservations();
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
