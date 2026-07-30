let onlineOrders = [];

const COLUMNS = {
  pending: ["pending", "confirmed"],
  preparing: ["preparing"],
  ready: ["ready"],
  completed: ["completed"],
};

const NEXT_STATUS = {
  pending: "preparing",
  confirmed: "preparing",
  preparing: "ready",
  ready: "completed",
};

async function init() {
  const user = await renderNav("online-orders.html");
  if (!hasPermission(user, "orders.fulfill")) {
    document.querySelector(".page").innerHTML = `<div class="empty-state">You do not have permission to view online orders.</div>`;
    return;
  }
  await loadOrders();
  setInterval(loadOrders, 15000);
  connectOrdersWebSocket(() => loadOrders());
}

async function loadOrders() {
  try {
    const all = await apiFetch("/orders?limit=200");
    onlineOrders = all.filter((o) => o.fulfillment_type && o.fulfillment_status !== "cancelled");
    render();
  } catch (err) {
    showToast(err.message, "error");
  }
}

function render() {
  const emptyState = document.getElementById("empty-state");
  emptyState.style.display = onlineOrders.length === 0 ? "block" : "none";

  for (const [col, statuses] of Object.entries(COLUMNS)) {
    const rows = onlineOrders.filter((o) => statuses.includes(o.fulfillment_status));
    const container = document.getElementById(`col-${col}`);
    container.innerHTML = rows.length
      ? rows.map(orderCardHtml).join("")
      : `<div class="empty-state" style="padding:12px;">—</div>`;
  }
}

function orderCardHtml(o) {
  const who = escapeHtml(o.guest_name || `Customer #${o.customer_id}`);
  const items = o.items.map((it) => `${it.qty}x #${it.product_id}`).join(", ");
  const next = NEXT_STATUS[o.fulfillment_status];
  const actionBtn = next
    ? `<button class="btn btn-primary btn-sm" onclick="advance(${o.id}, '${next}')">Mark ${next}</button>`
    : "";
  const cancelBtn =
    o.fulfillment_status !== "completed"
      ? `<button class="btn btn-secondary btn-sm" onclick="advance(${o.id}, 'cancelled')">Cancel</button>`
      : "";

  return `
    <div class="card" style="margin-bottom:10px; padding:12px;">
      <div style="display:flex; justify-content:space-between; font-weight:600;">
        <span>#${o.id} — ${o.fulfillment_type}</span>
        <span>${formatMoney(o.total)}</span>
      </div>
      <div style="font-size:13px; color:var(--text-muted); margin:4px 0;">${who}</div>
      <div style="font-size:13px; margin-bottom:8px;">${escapeHtml(items)}</div>
      ${o.delivery_address ? `<div style="font-size:12px; color:var(--text-muted); margin-bottom:8px;">${escapeHtml(o.delivery_address)}</div>` : ""}
      <div style="display:flex; gap:6px;">${actionBtn}${cancelBtn}</div>
    </div>
  `;
}

async function advance(orderId, status) {
  try {
    await apiFetch(`/orders/${orderId}/fulfillment-status`, {
      method: "PATCH",
      body: JSON.stringify({ status }),
    });
    await loadOrders();
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
