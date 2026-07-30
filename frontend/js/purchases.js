let allProducts = [];
let suppliers = [];
let purchases = [];
let purchaseCart = {}; // product_id -> { product, qty, unit_cost }
let selectedPurchase = null;

async function init() {
  const user = await renderNav("purchases.html");
  if (!hasPermission(user, "purchases.manage")) {
    document.querySelector(".page").innerHTML = `<div class="empty-state">You do not have permission to manage purchases.</div>`;
    return;
  }
  await Promise.all([loadProducts(), loadSuppliers(), loadHistory()]);
  wireEvents();
}

async function loadProducts() {
  allProducts = await apiFetch("/products?store_id=1&active_only=false");
}

async function loadSuppliers() {
  try {
    suppliers = await apiFetch("/suppliers");
    const select = document.getElementById("pu-supplier");
    select.innerHTML =
      `<option value="">— none —</option>` +
      suppliers.map((s) => `<option value="${s.id}">${escapeHtml(s.name)}</option>`).join("");
  } catch (err) {
    showToast(err.message, "error");
  }
}

async function loadHistory() {
  try {
    purchases = await apiFetch("/purchases?limit=100");
    renderHistory();
  } catch (err) {
    showToast(err.message, "error");
  }
}

function wireEvents() {
  document.getElementById("pu-search").addEventListener("input", (e) => {
    const term = e.target.value.trim().toLowerCase();
    const resultsBox = document.getElementById("pu-search-results");
    if (!term) {
      resultsBox.innerHTML = "";
      return;
    }
    const matches = allProducts
      .filter((p) => p.name.toLowerCase().includes(term) || p.sku.toLowerCase().includes(term))
      .slice(0, 8);
    resultsBox.innerHTML = matches
      .map(
        (p) => `
        <div class="cart-item" style="cursor:pointer;" onclick="addToPurchase(${p.id})">
          <span>${escapeHtml(p.name)} <span style="color:#6b7280;font-size:12px;">(${escapeHtml(p.sku)})</span></span>
          <span>${formatMoney(p.cost)}</span>
        </div>`
      )
      .join("") || `<div class="empty-state">No matches.</div>`;
  });

  document.getElementById("pu-discount").addEventListener("input", updateTotals);
}

function addToPurchase(productId) {
  const product = allProducts.find((p) => p.id === productId);
  if (!product) return;
  if (purchaseCart[productId]) {
    purchaseCart[productId].qty += 1;
  } else {
    purchaseCart[productId] = { product, qty: 1, unit_cost: Number(product.cost) || 0 };
  }
  document.getElementById("pu-search").value = "";
  document.getElementById("pu-search-results").innerHTML = "";
  renderPurchaseCart();
}

function updatePurchaseLine(productId, field, value) {
  const item = purchaseCart[productId];
  if (!item) return;
  if (field === "qty") {
    const qty = parseInt(value, 10);
    if (!qty || qty <= 0) return;
    item.qty = qty;
  } else if (field === "unit_cost") {
    const cost = parseFloat(value);
    if (isNaN(cost) || cost < 0) return;
    item.unit_cost = cost;
  }
  updateTotals();
}

function removeFromPurchase(productId) {
  delete purchaseCart[productId];
  renderPurchaseCart();
}

function renderPurchaseCart() {
  const tbody = document.getElementById("pu-cart-rows");
  const emptyState = document.getElementById("pu-cart-empty");
  const items = Object.values(purchaseCart);

  if (items.length === 0) {
    tbody.innerHTML = "";
    emptyState.style.display = "block";
  } else {
    emptyState.style.display = "none";
    tbody.innerHTML = items
      .map(({ product, qty, unit_cost }) => {
        const lineTotal = qty * unit_cost;
        return `
          <tr>
            <td>${escapeHtml(product.name)}</td>
            <td><input type="number" min="1" value="${qty}" style="margin:0; width:70px;" onchange="updatePurchaseLine(${product.id}, 'qty', this.value)" /></td>
            <td><input type="number" min="0" step="0.01" value="${unit_cost}" style="margin:0; width:90px;" onchange="updatePurchaseLine(${product.id}, 'unit_cost', this.value)" /></td>
            <td>${formatMoney(lineTotal)}</td>
            <td><button class="qty-btn" onclick="removeFromPurchase(${product.id})" title="Remove">×</button></td>
          </tr>
        `;
      })
      .join("");
  }
  updateTotals();
}

function updateTotals() {
  let subtotal = 0;
  let tax = 0;
  Object.values(purchaseCart).forEach(({ product, qty, unit_cost }) => {
    const lineSubtotal = qty * unit_cost;
    subtotal += lineSubtotal;
    tax += lineSubtotal * (product.tax_rate / 100);
  });
  const discount = parseFloat(document.getElementById("pu-discount").value || "0");
  const total = Math.max(0, subtotal + tax - discount);

  document.getElementById("pu-subtotal").textContent = formatMoney(subtotal);
  document.getElementById("pu-tax").textContent = formatMoney(tax);
  document.getElementById("pu-total").textContent = formatMoney(total);
  document.getElementById("pu-save-btn").disabled = Object.keys(purchaseCart).length === 0;
}

async function savePurchase() {
  const items = Object.values(purchaseCart).map(({ product, qty, unit_cost }) => ({
    product_id: product.id,
    qty,
    unit_cost,
    tax_rate: product.tax_rate,
  }));
  const supplierVal = document.getElementById("pu-supplier").value;
  const payload = {
    store_id: 1,
    items,
    discount_total: parseFloat(document.getElementById("pu-discount").value || "0"),
  };
  if (supplierVal) payload.supplier_id = parseInt(supplierVal, 10);
  const invoice = document.getElementById("pu-invoice").value.trim();
  if (invoice) payload.invoice_number = invoice;

  const btn = document.getElementById("pu-save-btn");
  btn.disabled = true;
  try {
    await apiFetch("/purchases", { method: "POST", body: JSON.stringify(payload) });
    showToast("Purchase saved — stock updated");
    purchaseCart = {};
    document.getElementById("pu-invoice").value = "";
    document.getElementById("pu-discount").value = "0";
    renderPurchaseCart();
    await loadProducts();
    await loadHistory();
  } catch (err) {
    showToast(err.message, "error");
    btn.disabled = false;
  }
}

function statusBadge(status) {
  const map = { completed: "badge-ok", returned: "badge-low", partially_returned: "badge-low" };
  return `<span class="badge ${map[status] || "badge-ok"}">${status.replace("_", " ")}</span>`;
}

function dueBadge(due) {
  return due > 0.004
    ? `<span class="badge badge-low">${formatMoney(due)}</span>`
    : `<span class="badge badge-ok">Paid</span>`;
}

function renderHistory() {
  const tbody = document.getElementById("history-rows");
  const emptyState = document.getElementById("history-empty");

  if (purchases.length === 0) {
    tbody.innerHTML = "";
    emptyState.style.display = "block";
    return;
  }
  emptyState.style.display = "none";

  tbody.innerHTML = purchases
    .map((p) => {
      const supplier = suppliers.find((s) => s.id === p.supplier_id);
      const itemCount = p.items.reduce((sum, i) => sum + i.qty, 0);
      return `
        <tr>
          <td>#${p.id}</td>
          <td>${formatDate(p.created_at)}</td>
          <td>${supplier ? escapeHtml(supplier.name) : "—"}</td>
          <td>${itemCount} item(s)</td>
          <td>${formatMoney(p.total)}</td>
          <td>${formatMoney(p.paid_amount)}</td>
          <td>${dueBadge(p.due_amount)}</td>
          <td>${statusBadge(p.status)}</td>
          <td><button class="btn btn-secondary btn-sm" onclick="openPurchaseModal(${p.id})">View / Return</button></td>
        </tr>
      `;
    })
    .join("");
}

async function openPurchaseModal(purchaseId) {
  try {
    selectedPurchase = await apiFetch(`/purchases/${purchaseId}`);
  } catch (err) {
    showToast(err.message, "error");
    return;
  }

  document.getElementById("pd-id").textContent = selectedPurchase.id;
  document.getElementById("pd-items").innerHTML = selectedPurchase.items
    .map((item) => {
      const product = allProducts.find((p) => p.id === item.product_id);
      const name = product ? product.name : `#${item.product_id}`;
      return `<div class="cart-item"><span>${item.qty}x ${escapeHtml(name)}${item.returned_qty ? ` (${item.returned_qty} returned)` : ""}</span><span>${formatMoney(item.line_total)}</span></div>`;
    })
    .join("");
  document.getElementById("pd-subtotal").textContent = formatMoney(selectedPurchase.subtotal);
  document.getElementById("pd-tax").textContent = formatMoney(selectedPurchase.tax_total);
  document.getElementById("pd-total").textContent = formatMoney(selectedPurchase.total);
  document.getElementById("pd-paid").textContent = formatMoney(selectedPurchase.paid_amount);
  document.getElementById("pd-due").textContent = formatMoney(selectedPurchase.due_amount);

  const paymentHistory = document.getElementById("payment-history");
  if (selectedPurchase.payments.length === 0) {
    paymentHistory.innerHTML = "";
  } else {
    paymentHistory.innerHTML =
      `<label>Payment History</label>` +
      selectedPurchase.payments
        .map(
          (p) =>
            `<div class="cart-item"><span>${p.payment_date} — ${escapeHtml(paymentMethodLabelPU(p.method))}${p.note ? ` (${escapeHtml(p.note)})` : ""}</span><span>${formatMoney(p.amount)}</span></div>`
        )
        .join("");
  }

  document.getElementById("pay-amount").value = "";
  document.getElementById("pay-date").value = new Date().toISOString().slice(0, 10);
  document.getElementById("pay-note").value = "";
  document.getElementById("payment-section").style.display = selectedPurchase.due_amount > 0.004 ? "block" : "none";

  const returnable = selectedPurchase.items.filter((i) => i.returned_qty < i.qty);
  const returnSection = document.getElementById("return-section");
  if (returnable.length === 0) {
    returnSection.style.display = "none";
  } else {
    returnSection.style.display = "block";
    document.getElementById("return-reason").value = "";
    document.getElementById("return-items").innerHTML = returnable
      .map((item) => {
        const product = allProducts.find((p) => p.id === item.product_id);
        const name = product ? product.name : `#${item.product_id}`;
        const remaining = item.qty - item.returned_qty;
        return `
          <div class="form-row" style="align-items:center;">
            <div style="flex:2;">${escapeHtml(name)} <span style="color:#6b7280;font-size:12px;">(max ${remaining})</span></div>
            <div style="flex:1;">
              <input type="number" min="0" max="${remaining}" value="0" data-product-id="${item.product_id}" class="return-qty-input" style="margin:0;" />
            </div>
          </div>
        `;
      })
      .join("");
  }

  document.getElementById("purchase-modal").style.display = "flex";
}

function closePurchaseModal() {
  document.getElementById("purchase-modal").style.display = "none";
  selectedPurchase = null;
}

async function submitPurchaseReturn() {
  if (!selectedPurchase) return;
  const reason = document.getElementById("return-reason").value.trim();
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
    await apiFetch(`/purchases/${selectedPurchase.id}/return`, {
      method: "POST",
      body: JSON.stringify({ reason, items }),
    });
    showToast("Return processed");
    closePurchaseModal();
    await loadProducts();
    await loadHistory();
  } catch (err) {
    showToast(err.message, "error");
  }
}

function paymentMethodLabelPU(method) {
  const labels = { bkash: "bKash", nagad: "Nagad", rocket: "Rocket", card: "Card", other: "Other", cash: "Cash" };
  return labels[method] || method;
}

async function submitPurchasePayment() {
  if (!selectedPurchase) return;
  const amount = parseFloat(document.getElementById("pay-amount").value);
  if (!amount || amount <= 0) {
    showToast("Enter a payment amount", "error");
    return;
  }
  const payload = {
    amount,
    payment_date: document.getElementById("pay-date").value,
    method: document.getElementById("pay-method").value,
    note: document.getElementById("pay-note").value.trim() || null,
  };

  try {
    await apiFetch(`/purchases/${selectedPurchase.id}/payments`, {
      method: "POST",
      body: JSON.stringify(payload),
    });
    showToast("Payment recorded");
    await loadHistory();
    await openPurchaseModal(selectedPurchase.id);
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
