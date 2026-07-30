let allProducts = [];
let allCustomers = [];
let selectedCustomer = null;
let cart = {}; // product_id -> { product, qty }
let currentUser = null;
let appliedDiscount = null; // { id, code, name, type, value }
let html5QrCode = null;
let scannerBusy = false;
let heldSales = [];
let lastReceiptBodyHtml = "";
let tableIdFromQuery = null;

async function init() {
  currentUser = await renderNav("pos.html");
  tableIdFromQuery = new URLSearchParams(window.location.search).get("table_id");
  if (tableIdFromQuery) {
    const banner = document.createElement("div");
    banner.className = "badge badge-warning";
    banner.style.cssText = "display:block; width:fit-content; margin: 0 auto 12px;";
    banner.textContent = `Order for Table (#${tableIdFromQuery})`;
    const page = document.querySelector(".page");
    if (page) page.prepend(banner);
  }
  await loadProducts();
  await loadCustomers();
  wireEvents();
  await refreshHeldCount();
}

async function loadCustomers() {
  try {
    allCustomers = await apiFetch("/customers");
  } catch (err) {
    // Non-critical for checkout; customer selection just won't have data to search
  }
}

async function loadProducts() {
  try {
    allProducts = await apiFetch("/products?store_id=1&active_only=true");
    renderProductGrid(allProducts);
  } catch (err) {
    showToast(err.message, "error");
  }
}

function renderProductGrid(products) {
  const grid = document.getElementById("product-grid");
  if (products.length === 0) {
    grid.innerHTML = `<div class="empty-state">No products found.</div>`;
    return;
  }
  grid.innerHTML = products
    .map((p) => {
      const outOfStock = p.quantity <= 0;
      const thumb = p.image_url
        ? `<img class="thumb" src="${p.image_url}" />`
        : `<div class="thumb-placeholder">📦</div>`;
      return `
        <div class="product-tile ${outOfStock ? "out-of-stock" : ""}" data-id="${p.id}">
          ${thumb}
          <div class="name">${escapeHtml(p.name)}</div>
          <div class="price">${formatMoney(p.price)}</div>
          <div class="stock">${outOfStock ? "Out of stock" : p.quantity + " in stock"}</div>
        </div>
      `;
    })
    .join("");

  grid.querySelectorAll(".product-tile").forEach((tile) => {
    tile.addEventListener("click", () => {
      if (tile.classList.contains("out-of-stock")) return;
      const id = parseInt(tile.dataset.id, 10);
      const product = allProducts.find((p) => p.id === id);
      addToCart(product);
    });
  });
}

function addToCart(product) {
  const existing = cart[product.id];
  const currentQty = existing ? existing.qty : 0;
  if (currentQty + 1 > product.quantity) {
    showToast(`Only ${product.quantity} in stock`, "error");
    return;
  }
  if (existing) {
    existing.qty += 1;
  } else {
    cart[product.id] = { product, qty: 1 };
  }
  renderCart();
}

function changeQty(productId, delta) {
  const item = cart[productId];
  if (!item) return;
  const newQty = item.qty + delta;
  if (newQty <= 0) {
    delete cart[productId];
  } else if (newQty > item.product.quantity) {
    showToast(`Only ${item.product.quantity} in stock`, "error");
    return;
  } else {
    item.qty = newQty;
  }
  renderCart();
}

function removeFromCart(productId) {
  delete cart[productId];
  renderCart();
}

function renderCart() {
  const container = document.getElementById("cart-items");
  const emptyState = document.getElementById("cart-empty");
  const items = Object.values(cart);

  if (items.length === 0) {
    container.innerHTML = "";
    emptyState.style.display = "block";
  } else {
    emptyState.style.display = "none";
    container.innerHTML = items
      .map(({ product, qty }) => {
        return `
          <div class="cart-item">
            <div>
              <div>${escapeHtml(product.name)}</div>
              <div style="color:#6b7280;font-size:12px;">${formatMoney(product.price)} each</div>
            </div>
            <div class="qty-controls">
              <button class="qty-btn" onclick="changeQty(${product.id}, -1)">−</button>
              <span>${qty}</span>
              <button class="qty-btn" onclick="changeQty(${product.id}, 1)">+</button>
              <button class="qty-btn" onclick="removeFromCart(${product.id})" title="Remove">×</button>
            </div>
          </div>
        `;
      })
      .join("");
  }

  updateTotals();
}

function currentSubtotal() {
  let subtotal = 0;
  Object.values(cart).forEach(({ product, qty }) => {
    subtotal += product.price * qty;
  });
  return subtotal;
}

function discountAmountFor(subtotal, tax) {
  if (!appliedDiscount) return 0;
  const raw =
    appliedDiscount.type === "percentage"
      ? subtotal * (appliedDiscount.value / 100)
      : appliedDiscount.value;
  return Math.min(raw, subtotal + tax);
}

function updateTotals() {
  let subtotal = 0;
  let tax = 0;
  Object.values(cart).forEach(({ product, qty }) => {
    const lineSubtotal = product.price * qty;
    subtotal += lineSubtotal;
    tax += lineSubtotal * (product.tax_rate / 100);
  });
  const discount = discountAmountFor(subtotal, tax);
  const total = subtotal + tax - discount;

  document.getElementById("t-subtotal").textContent = formatMoney(subtotal);
  document.getElementById("t-tax").textContent = formatMoney(tax);

  const discountRow = document.getElementById("discount-row");
  if (discount > 0) {
    discountRow.style.display = "flex";
    document.getElementById("t-discount").textContent = "-" + formatMoney(discount);
  } else {
    discountRow.style.display = "none";
  }

  document.getElementById("t-total").textContent = formatMoney(total);

  document.getElementById("checkout-btn").disabled = Object.keys(cart).length === 0;
  document.getElementById("hold-btn").disabled = Object.keys(cart).length === 0;

  // Pre-fill tendered with the exact total for convenience
  const tenderedInput = document.getElementById("tendered");
  if (document.getElementById("payment-method").value === "cash") {
    tenderedInput.value = total.toFixed(2);
  }
}

async function applyDiscount() {
  const code = document.getElementById("discount-code").value.trim();
  if (!code) return;

  const subtotal = currentSubtotal();
  try {
    const preview = await apiFetch(`/discounts/lookup/${encodeURIComponent(code)}?subtotal=${subtotal}`);
    appliedDiscount = preview;
    const badge = document.getElementById("discount-applied");
    badge.style.display = "block";
    badge.innerHTML = `"${escapeHtml(preview.code)}" applied — ${escapeHtml(preview.name)} <a href="#" onclick="removeDiscount(); return false;" style="color:var(--danger);">(remove)</a>`;
    updateTotals();
    showToast("Discount applied");
  } catch (err) {
    appliedDiscount = null;
    document.getElementById("discount-applied").style.display = "none";
    updateTotals();
    showToast(err.message, "error");
  }
}

function removeDiscount() {
  appliedDiscount = null;
  document.getElementById("discount-code").value = "";
  document.getElementById("discount-applied").style.display = "none";
  updateTotals();
}

function wireEvents() {
  document.getElementById("search").addEventListener("input", (e) => {
    const term = e.target.value.toLowerCase();
    const filtered = allProducts.filter(
      (p) => p.name.toLowerCase().includes(term) || p.sku.toLowerCase().includes(term)
    );
    renderProductGrid(filtered);
  });

  const mobileMoneyMethods = ["bkash", "nagad", "rocket"];
  document.getElementById("payment-method").addEventListener("change", (e) => {
    document.getElementById("cash-tendered-wrap").style.display = e.target.value === "cash" ? "block" : "none";
    document.getElementById("payment-reference-wrap").style.display = mobileMoneyMethods.includes(e.target.value) ? "block" : "none";
    updateTotals();
  });

  document.getElementById("checkout-btn").addEventListener("click", submitOrder);

  document.getElementById("customer-search").addEventListener("input", (e) => {
    const term = e.target.value.trim().toLowerCase();
    const resultsBox = document.getElementById("customer-search-results");
    if (!term) {
      resultsBox.classList.remove("open");
      return;
    }
    const matches = allCustomers
      .filter((c) => c.name.toLowerCase().includes(term) || (c.phone || "").toLowerCase().includes(term))
      .slice(0, 6);
    resultsBox.innerHTML =
      matches
        .map(
          (c) => `
        <div class="result-item" onclick="selectCustomer(${c.id})">
          <div>${escapeHtml(c.name)}</div>
          <div class="sub">${escapeHtml(c.phone || "no phone")} — ${c.loyalty_points} pts</div>
        </div>`
        )
        .join("") || `<div class="result-item" style="cursor:default; color:#6b7280;">No matches</div>`;
    resultsBox.classList.add("open");
  });

  document.addEventListener("click", (e) => {
    if (!e.target.closest("#customer-search-wrap")) {
      document.getElementById("customer-search-results").classList.remove("open");
    }
  });

  document.getElementById("quick-add-customer-form").addEventListener("submit", submitQuickAddCustomer);
  document.getElementById("hold-form").addEventListener("submit", submitHold);
}

function selectCustomer(customerId) {
  const customer = allCustomers.find((c) => c.id === customerId);
  if (!customer) return;
  selectedCustomer = customer;

  document.getElementById("customer-search-wrap").style.display = "none";
  document.getElementById("customer-search-results").classList.remove("open");
  document.getElementById("customer-search").value = "";

  const badge = document.getElementById("customer-selected");
  badge.style.display = "flex";
  document.getElementById("customer-selected-label").textContent = `${customer.name}${customer.phone ? ` (${customer.phone})` : ""} — ${customer.loyalty_points} pts`;
}

function removeCustomer() {
  selectedCustomer = null;
  document.getElementById("customer-search-wrap").style.display = "flex";
  document.getElementById("customer-selected").style.display = "none";
}

function openQuickAddCustomer() {
  document.getElementById("qc-name").value = "";
  document.getElementById("qc-phone").value = "";
  document.getElementById("quick-add-customer-modal").style.display = "flex";
}

function closeQuickAddCustomer() {
  document.getElementById("quick-add-customer-modal").style.display = "none";
}

async function submitQuickAddCustomer(e) {
  e.preventDefault();
  const payload = {
    name: document.getElementById("qc-name").value.trim(),
    phone: document.getElementById("qc-phone").value.trim() || null,
  };
  try {
    const customer = await apiFetch("/customers", { method: "POST", body: JSON.stringify(payload) });
    allCustomers.push(customer);
    closeQuickAddCustomer();
    selectCustomer(customer.id);
    showToast("Customer added");
  } catch (err) {
    showToast(err.message, "error");
  }
}

async function submitOrder() {
  const paymentMethod = document.getElementById("payment-method").value;
  const tenderedRaw = document.getElementById("tendered").value;

  const items = Object.values(cart).map(({ product, qty }) => ({
    product_id: product.id,
    qty,
  }));

  const payload = {
    store_id: 1,
    items,
    payment_method: paymentMethod,
  };
  if (paymentMethod === "cash") {
    payload.tendered = parseFloat(tenderedRaw || "0");
  }
  if (["bkash", "nagad", "rocket"].includes(paymentMethod)) {
    const reference = document.getElementById("payment-reference").value.trim();
    if (reference) payload.payment_reference = reference;
  }
  if (appliedDiscount) {
    payload.discount_code = appliedDiscount.code;
  }
  if (selectedCustomer) {
    payload.customer_id = selectedCustomer.id;
  }
  if (tableIdFromQuery) {
    payload.table_id = parseInt(tableIdFromQuery, 10);
  }

  const btn = document.getElementById("checkout-btn");
  btn.disabled = true;
  btn.textContent = "Processing...";

  try {
    const order = await apiFetch("/orders", { method: "POST", body: JSON.stringify(payload) });
    showReceipt(order);
    cart = {};
    removeDiscount();
    removeCustomer();
    document.getElementById("payment-reference").value = "";
    renderCart();
    await loadProducts(); // refresh stock levels
    await loadCustomers(); // refresh loyalty points / totals
  } catch (err) {
    showToast(err.message, "error");
  } finally {
    btn.disabled = Object.keys(cart).length === 0;
    btn.textContent = "Complete Sale";
  }
}

function buildReceiptBodyHtml(order) {
  const lines = order.items
    .map((item) => {
      const product = allProducts.find((p) => p.id === item.product_id);
      const name = product ? product.name : `#${item.product_id}`;
      return `<div class="receipt-line"><span>${item.qty}x ${escapeHtml(name)}</span><span>${formatMoney(item.line_total)}</span></div>`;
    })
    .join("");

  const businessName = _businessSettings ? _businessSettings.business_name : "DokanPro";
  const footer = _businessSettings && _businessSettings.receipt_footer ? _businessSettings.receipt_footer : "Thank you!";

  return `
    <div style="text-align:center;font-weight:bold;">${escapeHtml(businessName).toUpperCase()}</div>
    <div style="text-align:center;font-size:11px;">Order #${order.id} — ${formatDate(order.created_at)}</div>
    ${selectedCustomer ? `<div style="text-align:center;font-size:11px;">Customer: ${escapeHtml(selectedCustomer.name)}</div>` : ""}
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
}

function showReceipt(order) {
  lastReceiptBodyHtml = buildReceiptBodyHtml(order);

  const html = `
    <div class="receipt-overlay" id="receipt-overlay">
      <div class="receipt-box">
        ${lastReceiptBodyHtml}
        <button class="btn btn-primary btn-block" style="margin-top:14px;" onclick="printReceipt()">🖨 Print Receipt</button>
        <button class="btn btn-secondary btn-block" style="margin-top:8px;" onclick="document.getElementById('receipt-overlay').remove()">Close</button>
      </div>
    </div>
  `;
  document.getElementById("receipt-container").innerHTML = html;
}

function printReceipt() {
  const printArea = document.getElementById("print-area");
  printArea.innerHTML = `<div class="receipt-box" style="width:auto; max-width:320px; margin:0 auto;">${lastReceiptBodyHtml}</div>`;
  window.print();
}

function paymentMethodLabel(method) {
  const labels = { bkash: "bKash", nagad: "Nagad", rocket: "Rocket", card: "Card", mobile: "Mobile", other: "Other" };
  return labels[method] || method;
}

function escapeHtml(str) {
  const div = document.createElement("div");
  div.textContent = str;
  return div.innerHTML;
}

function openScanner() {
  document.getElementById("scanner-overlay").style.display = "flex";
  scannerBusy = false;
  html5QrCode = new Html5Qrcode("scanner-view");
  html5QrCode
    .start(
      { facingMode: "environment" },
      { fps: 10, qrbox: { width: 250, height: 150 } },
      onScanSuccess
    )
    .catch((err) => {
      showToast("Could not access camera: " + err, "error");
      closeScanner();
    });
}

function onScanSuccess(decodedText) {
  if (scannerBusy) return;
  scannerBusy = true;

  const code = decodedText.trim().toLowerCase();
  const product = allProducts.find((p) => p.sku.toLowerCase() === code);

  closeScanner();

  if (!product) {
    showToast(`No product found for barcode "${decodedText}"`, "error");
    return;
  }
  addToCart(product);
  showToast(`Added ${product.name}`);
}

function closeScanner() {
  document.getElementById("scanner-overlay").style.display = "none";
  if (html5QrCode) {
    const instance = html5QrCode;
    html5QrCode = null;
    instance
      .stop()
      .then(() => instance.clear())
      .catch(() => {});
  }
}

async function refreshHeldCount() {
  try {
    heldSales = await apiFetch("/held-sales?store_id=1");
    const badge = document.getElementById("held-count-badge");
    badge.style.display = heldSales.length > 0 ? "inline-block" : "none";
    badge.textContent = heldSales.length;
  } catch (err) {
    // Non-critical
  }
}

function openHoldModal() {
  if (Object.keys(cart).length === 0) return;
  document.getElementById("hold-note").value = "";
  document.getElementById("hold-modal").style.display = "flex";
}

function closeHoldModal() {
  document.getElementById("hold-modal").style.display = "none";
}

async function submitHold(e) {
  e.preventDefault();
  const items = Object.values(cart).map(({ product, qty }) => ({ product_id: product.id, qty }));
  const payload = {
    store_id: 1,
    items,
    note: document.getElementById("hold-note").value.trim() || null,
  };
  if (selectedCustomer) payload.customer_id = selectedCustomer.id;
  if (appliedDiscount) payload.discount_code = appliedDiscount.code;

  try {
    await apiFetch("/held-sales", { method: "POST", body: JSON.stringify(payload) });
    cart = {};
    removeDiscount();
    removeCustomer();
    renderCart();
    closeHoldModal();
    await refreshHeldCount();
    showToast("Sale held");
  } catch (err) {
    showToast(err.message, "error");
  }
}

async function openHeldSalesModal() {
  try {
    heldSales = await apiFetch("/held-sales?store_id=1");
  } catch (err) {
    showToast(err.message, "error");
    return;
  }

  const list = document.getElementById("held-sales-list");
  if (heldSales.length === 0) {
    list.innerHTML = `<div class="empty-state">No held sales.</div>`;
  } else {
    list.innerHTML = heldSales
      .map((h) => {
        const itemCount = h.items.reduce((sum, i) => sum + i.qty, 0);
        const customer = h.customer_id ? allCustomers.find((c) => c.id === h.customer_id) : null;
        return `
          <div class="cart-item">
            <div>
              <div>${escapeHtml(h.note || `Held sale #${h.id}`)}</div>
              <div style="color:#6b7280;font-size:12px;">
                ${itemCount} item(s) — ${escapeHtml(h.created_by_name)} — ${formatDate(h.created_at)}
                ${customer ? ` — ${escapeHtml(customer.name)}` : ""}
              </div>
            </div>
            <div style="display:flex; gap:6px;">
              <button class="btn btn-primary btn-sm" onclick="resumeHeldSale(${h.id})">Resume</button>
              <button class="btn btn-danger btn-sm" onclick="deleteHeldSale(${h.id})">Delete</button>
            </div>
          </div>
        `;
      })
      .join("");
  }

  document.getElementById("held-sales-modal").style.display = "flex";
}

function closeHeldSalesModal() {
  document.getElementById("held-sales-modal").style.display = "none";
}

async function resumeHeldSale(heldSaleId) {
  const held = heldSales.find((h) => h.id === heldSaleId);
  if (!held) return;

  if (Object.keys(cart).length > 0) {
    if (!confirm("Resuming will replace your current cart. Continue?")) return;
  }

  cart = {};
  held.items.forEach((item) => {
    const product = allProducts.find((p) => p.id === item.product_id);
    if (product) cart[product.id] = { product, qty: item.qty };
  });

  removeCustomer();
  if (held.customer_id) {
    const customer = allCustomers.find((c) => c.id === held.customer_id);
    if (customer) selectCustomer(customer.id);
  }

  removeDiscount();
  if (held.discount_code) {
    document.getElementById("discount-code").value = held.discount_code;
    await applyDiscount();
  }

  try {
    await apiFetch(`/held-sales/${heldSaleId}`, { method: "DELETE" });
  } catch (err) {
    // Non-critical: worst case the held record lingers and can be deleted manually
  }

  renderCart();
  closeHeldSalesModal();
  await refreshHeldCount();
  showToast("Sale resumed");
}

async function deleteHeldSale(heldSaleId) {
  try {
    await apiFetch(`/held-sales/${heldSaleId}`, { method: "DELETE" });
    showToast("Held sale removed");
    await openHeldSalesModal();
    await refreshHeldCount();
  } catch (err) {
    showToast(err.message, "error");
  }
}

init();
