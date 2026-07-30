let kitchenOrders = [];

const NEXT_STATUS = { confirmed: "preparing", preparing: "ready" };
const NEXT_LABEL = { confirmed: "Start Preparing", preparing: "Mark Ready" };

async function init() {
  const user = await renderNav("kitchen-display.html");
  if (!hasPermission(user, "orders.fulfill")) {
    document.querySelector(".page").innerHTML = `<div class="empty-state">You do not have permission to view the kitchen display.</div>`;
    return;
  }
  await loadOrders();
  setInterval(loadOrders, 15000);
  connectOrdersWebSocket(() => loadOrders());
}

async function loadOrders() {
  try {
    const all = await apiFetch("/orders?limit=200");
    kitchenOrders = all.filter(
      (o) => o.fulfillment_type && ["confirmed", "preparing"].includes(o.fulfillment_status)
    );
    kitchenOrders.sort((a, b) => a.id - b.id);
    render();
  } catch (err) {
    showToast(err.message, "error");
  }
}

function render() {
  const grid = document.getElementById("kitchen-grid");
  const emptyState = document.getElementById("empty-state");

  if (kitchenOrders.length === 0) {
    grid.innerHTML = "";
    emptyState.style.display = "block";
    return;
  }
  emptyState.style.display = "none";

  grid.innerHTML = kitchenOrders.map(orderCardHtml).join("");
}

function orderSource(o) {
  if (o.fulfillment_type === "dine_in") return `Table ${o.table_label || "?"}`;
  if (o.fulfillment_type === "delivery") return "Delivery";
  return "Pickup";
}

function orderCardHtml(o) {
  const items = o.items
    .map((it) => {
      const note = it.special_instructions
        ? `<div class="item-note">⚠ ${escapeHtml(it.special_instructions)}</div>`
        : "";
      return `<div class="item-line">${it.qty}x ${escapeHtml(it.product_name || `#${it.product_id}`)}</div>${note}`;
    })
    .join("");

  const next = NEXT_STATUS[o.fulfillment_status];
  const nextLabel = NEXT_LABEL[o.fulfillment_status];

  return `
    <div class="kitchen-card">
      <div class="order-num">#${o.id}</div>
      <div class="order-source">${escapeHtml(orderSource(o))}</div>
      ${items}
      ${next ? `<button class="btn btn-primary btn-block kitchen-btn" onclick="advance(${o.id}, '${next}')">${nextLabel}</button>` : ""}
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
