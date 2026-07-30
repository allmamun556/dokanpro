const STATUS_LABELS = {
  pending: "Received",
  confirmed: "Confirmed — being prepared soon",
  preparing: "Preparing",
  ready: "Ready",
  completed: "Completed",
  cancelled: "Cancelled",
};

async function init() {
  await renderSiteNav("order-status.html");
  renderSiteFooter();

  const params = new URLSearchParams(window.location.search);
  const orderId = params.get("order_id");
  const email = params.get("email") || "";

  if (!orderId) {
    document.getElementById("status-card").innerHTML = `<div class="empty-state">No order specified.</div>`;
    return;
  }

  await load(orderId, email);
  setInterval(() => load(orderId, email), 10000);
}

async function load(orderId, email) {
  try {
    const query = email ? `?email=${encodeURIComponent(email)}` : "";
    const { order } = await apiFetch(`/checkout/${orderId}/status${query}`);
    render(order);
  } catch (err) {
    document.getElementById("status-card").innerHTML = `<div class="empty-state">${escapeHtml(err.message)}</div>`;
  }
}

function render(order) {
  const label = STATUS_LABELS[order.fulfillment_status] || order.fulfillment_status;
  const items = order.items.map((it) => `${it.qty}x item #${it.product_id}`).join(", ");

  document.getElementById("status-card").innerHTML = `
    <h3>Order #${order.id}</h3>
    <p><strong>${escapeHtml(label)}</strong></p>
    <p>${escapeHtml(order.fulfillment_type)} &middot; ${formatMoney(order.total)}</p>
    <p style="color:var(--text-muted); font-size:14px;">${escapeHtml(items)}</p>
    ${order.status === "voided" ? `<p style="color:var(--danger);">This order was cancelled and not charged.</p>` : ""}
  `;
}

init();
