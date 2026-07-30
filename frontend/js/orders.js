let orders = [];
let allProducts = [];
let allCustomers = [];
let currentUser = null;
let selectedOrder = null;

async function init() {
  currentUser = await renderNav("orders.html");
  await loadProducts();
  await loadCustomers();
  await loadOrders();
}

async function loadProducts() {
  try {
    allProducts = await apiFetch("/products?store_id=1&active_only=false");
  } catch (err) {
    // Non-critical for the order list; return UI just falls back to showing product IDs
  }
}

async function loadCustomers() {
  try {
    allCustomers = await apiFetch("/customers");
  } catch (err) {
    // Non-critical; falls back to not showing a customer name
  }
}

function productName(productId) {
  const product = allProducts.find((p) => p.id === productId);
  return product ? product.name : `#${productId}`;
}

function customerName(customerId) {
  const customer = allCustomers.find((c) => c.id === customerId);
  return customer ? customer.name : null;
}

async function loadOrders() {
  try {
    orders = await apiFetch("/orders?limit=100");
    renderTable();
  } catch (err) {
    showToast(err.message, "error");
  }
}

function statusBadge(status) {
  const map = {
    completed: "badge-ok",
    refunded: "badge-low",
    partially_refunded: "badge-low",
    voided: "badge-low",
  };
  return `<span class="badge ${map[status] || "badge-ok"}">${status.replace("_", " ")}</span>`;
}

function renderTable() {
  const tbody = document.getElementById("order-rows");
  const emptyState = document.getElementById("empty-state");

  if (orders.length === 0) {
    tbody.innerHTML = "";
    emptyState.style.display = "block";
    return;
  }
  emptyState.style.display = "none";

  const canRefund = currentUser && hasPermission(currentUser, "orders.refund");

  tbody.innerHTML = orders
    .map((o) => {
      const itemCount = o.items.reduce((sum, i) => sum + i.qty, 0);
      return `
        <tr>
          <td>#${o.id}</td>
          <td>${formatDate(o.created_at)}</td>
          <td>${o.customer_id ? escapeHtml(customerName(o.customer_id) || "—") : "—"}</td>
          <td>${itemCount} item(s)</td>
          <td>${formatMoney(o.total)}</td>
          <td>${escapeHtml(paymentMethodLabel(o.payment_method))}</td>
          <td>${statusBadge(o.status)}</td>
          <td>
            <button class="btn btn-secondary btn-sm" onclick="openOrderModal(${o.id})">View${canRefund ? " / Refund" : ""}</button>
          </td>
        </tr>
      `;
    })
    .join("");
}

function openOrderModal(orderId) {
  selectedOrder = orders.find((o) => o.id === orderId);
  if (!selectedOrder) return;

  document.getElementById("od-id").textContent = selectedOrder.id;
  const customerRow = document.getElementById("od-customer-row");
  const custName = selectedOrder.customer_id ? customerName(selectedOrder.customer_id) : null;
  if (custName) {
    customerRow.style.display = "block";
    document.getElementById("od-customer").textContent = custName;
  } else {
    customerRow.style.display = "none";
  }
  document.getElementById("od-items").innerHTML = selectedOrder.items
    .map(
      (item) =>
        `<div class="cart-item"><span>${item.qty}x ${escapeHtml(productName(item.product_id))}${item.returned_qty ? ` (${item.returned_qty} returned)` : ""}</span><span>${formatMoney(item.line_total)}</span></div>`
    )
    .join("");
  document.getElementById("od-subtotal").textContent = formatMoney(selectedOrder.subtotal);
  document.getElementById("od-tax").textContent = formatMoney(selectedOrder.tax_total);
  document.getElementById("od-total").textContent = formatMoney(selectedOrder.total);
  document.getElementById("od-payment").textContent = paymentMethodLabel(selectedOrder.payment_method);
  const referenceRow = document.getElementById("od-reference-row");
  if (selectedOrder.payment_reference) {
    referenceRow.style.display = "flex";
    document.getElementById("od-reference").textContent = selectedOrder.payment_reference;
  } else {
    referenceRow.style.display = "none";
  }

  const discountRow = document.getElementById("od-discount-row");
  if (selectedOrder.discount_total > 0) {
    discountRow.style.display = "flex";
    document.getElementById("od-discount-label").textContent = selectedOrder.discount_code
      ? `Discount (${selectedOrder.discount_code})`
      : "Discount";
    document.getElementById("od-discount").textContent = "-" + formatMoney(selectedOrder.discount_total);
  } else {
    discountRow.style.display = "none";
  }

  const canRefund = currentUser && hasPermission(currentUser, "orders.refund");
  const returnable = selectedOrder.items.filter((i) => i.returned_qty < i.qty);
  const refundSection = document.getElementById("refund-section");

  if (canRefund && returnable.length > 0) {
    refundSection.style.display = "block";
    document.getElementById("refund-reason").value = "";
    document.getElementById("return-items").innerHTML = returnable
      .map((item) => {
        const remaining = item.qty - item.returned_qty;
        return `
          <div class="form-row" style="align-items:center;">
            <div style="flex:2;">${escapeHtml(productName(item.product_id))} <span style="color:#6b7280;font-size:12px;">(max ${remaining})</span></div>
            <div style="flex:1;">
              <input type="number" min="0" max="${remaining}" value="0" data-product-id="${item.product_id}" class="return-qty-input" style="margin:0;" />
            </div>
          </div>
        `;
      })
      .join("");
  } else {
    refundSection.style.display = "none";
  }

  document.getElementById("order-modal").style.display = "flex";
}

function fillMaxReturnQty() {
  document.querySelectorAll(".return-qty-input").forEach((input) => {
    input.value = input.max;
  });
}

function closeOrderModal() {
  document.getElementById("order-modal").style.display = "none";
  selectedOrder = null;
}

async function submitRefund() {
  if (!selectedOrder) return;
  const reason = document.getElementById("refund-reason").value.trim();

  if (!reason) {
    showToast("Please provide a return reason", "error");
    return;
  }

  const items = Array.from(document.querySelectorAll(".return-qty-input"))
    .map((input) => ({ product_id: parseInt(input.dataset.productId, 10), qty: parseInt(input.value || "0", 10) }))
    .filter((i) => i.qty > 0);

  if (items.length === 0) {
    showToast("Enter a quantity to return for at least one item", "error");
    return;
  }

  try {
    await apiFetch(`/orders/${selectedOrder.id}/refund`, {
      method: "POST",
      body: JSON.stringify({ reason, items }),
    });
    showToast("Return processed");
    closeOrderModal();
    await loadOrders();
  } catch (err) {
    showToast(err.message, "error");
  }
}

async function downloadOrderInvoice() {
  if (!selectedOrder) return;
  try {
    await downloadFile(`/orders/${selectedOrder.id}/invoice`);
  } catch (err) {
    showToast(err.message, "error");
  }
}

function printOrderReceipt() {
  if (!selectedOrder) return;
  const order = selectedOrder;

  const lines = order.items
    .map(
      (item) =>
        `<div class="receipt-line"><span>${item.qty}x ${escapeHtml(productName(item.product_id))}</span><span>${formatMoney(item.line_total)}</span></div>`
    )
    .join("");

  const businessName = _businessSettings ? _businessSettings.business_name : "DokanPro";
  const footer = _businessSettings && _businessSettings.receipt_footer ? _businessSettings.receipt_footer : "Thank you!";
  const custName = order.customer_id ? customerName(order.customer_id) : null;

  const body = `
    <div style="text-align:center;font-weight:bold;">${escapeHtml(businessName).toUpperCase()}</div>
    <div style="text-align:center;font-size:11px;">Order #${order.id} — ${formatDate(order.created_at)}</div>
    ${custName ? `<div style="text-align:center;font-size:11px;">Customer: ${escapeHtml(custName)}</div>` : ""}
    <hr />
    ${lines}
    <hr />
    <div class="receipt-line"><span>Subtotal</span><span>${formatMoney(order.subtotal)}</span></div>
    <div class="receipt-line"><span>Tax</span><span>${formatMoney(order.tax_total)}</span></div>
    ${order.discount_total > 0 ? `<div class="receipt-line"><span>Discount${order.discount_code ? ` (${escapeHtml(order.discount_code)})` : ""}</span><span>-${formatMoney(order.discount_total)}</span></div>` : ""}
    <div class="receipt-line" style="font-weight:bold;"><span>Total</span><span>${formatMoney(order.total)}</span></div>
    ${order.payment_method === "cash" ? `
    <div class="receipt-line"><span>Tendered</span><span>${formatMoney(order.tendered)}</span></div>
    <div class="receipt-line"><span>Change</span><span>${formatMoney(order.change_given)}</span></div>
    ` : `<div class="receipt-line"><span>Paid via</span><span>${escapeHtml(paymentMethodLabel(order.payment_method))}</span></div>
    ${order.payment_reference ? `<div class="receipt-line"><span>Trx ID</span><span>${escapeHtml(order.payment_reference)}</span></div>` : ""}`}
    <hr />
    <div style="text-align:center;font-size:11px;">${escapeHtml(footer)}</div>
  `;

  document.getElementById("print-area").innerHTML = `<div class="receipt-box" style="width:auto; max-width:320px; margin:0 auto;">${body}</div>`;
  window.print();
}

function paymentMethodLabel(method) {
  const labels = { bkash: "bKash", nagad: "Nagad", rocket: "Rocket", card: "Card", mobile: "Mobile", other: "Other", cash: "Cash" };
  return labels[method] || method;
}

function escapeHtml(str) {
  const div = document.createElement("div");
  div.textContent = str;
  return div.innerHTML;
}

init();
