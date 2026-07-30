async function init() {
  requireCustomerAuth();
  await renderSiteNav("account.html");
  renderSiteFooter();

  try {
    const customer = await fetchCurrentCustomer();
    document.getElementById("profile-card").innerHTML = `
      <h3>${escapeHtml(customer.name)}</h3>
      <p>${escapeHtml(customer.email || "")}${customer.phone ? " &middot; " + escapeHtml(customer.phone) : ""}</p>
      <p>Loyalty points: <strong>${customer.loyalty_points}</strong></p>
    `;
  } catch (err) {
    window.location.href = "login.html";
    return;
  }

  await Promise.all([loadOrders(), loadReservations()]);
}

async function loadOrders() {
  try {
    const orders = await apiFetch("/account/orders");
    const el = document.getElementById("orders-list");
    el.innerHTML = orders.length
      ? orders
          .map(
            (o) => `
        <div class="cart-line">
          <div>
            <div>Order #${o.id} — ${escapeHtml(o.fulfillment_type || "in-store")}</div>
            <div style="font-size:12px; color:var(--text-muted);">${formatDate(o.created_at)} &middot; ${escapeHtml(o.fulfillment_status || o.status)}</div>
          </div>
          <div style="text-align:right;">
            <div>${formatMoney(o.total)}</div>
            <a href="#" style="font-size:12px;" onclick="downloadInvoice(event, ${o.id})">Download Invoice</a>
          </div>
        </div>
      `
          )
          .join("")
      : `<div class="empty-state">No orders yet.</div>`;
  } catch (err) {
    showToast(err.message, "error");
  }
}

async function loadReservations() {
  try {
    const reservations = await apiFetch("/account/reservations");
    const el = document.getElementById("reservations-list");
    el.innerHTML = reservations.length
      ? reservations
          .map(
            (r) => `
        <div class="cart-line">
          <div>
            <div>${formatDate(r.reservation_time)} &middot; Party of ${r.party_size}</div>
            <div style="font-size:12px; color:var(--text-muted);">${escapeHtml(r.status)}</div>
          </div>
        </div>
      `
          )
          .join("")
      : `<div class="empty-state">No reservations yet.</div>`;
  } catch (err) {
    showToast(err.message, "error");
  }
}

async function downloadInvoice(e, orderId) {
  e.preventDefault();
  try {
    await downloadFile(`/account/orders/${orderId}/invoice`);
  } catch (err) {
    showToast(err.message, "error");
  }
}

init();
