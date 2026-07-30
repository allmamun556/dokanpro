let allProducts = [];
let stores = [];
let transfers = [];

async function init() {
  const user = await renderNav("transfers.html");
  if (!hasPermission(user, "transfers.manage")) {
    document.querySelector(".page").innerHTML = `<div class="empty-state">You do not have permission to manage stock transfers.</div>`;
    return;
  }
  await Promise.all([loadProducts(), loadStores()]);
  await loadHistory();
  wireEvents();
  updateAvailable();
}

async function loadProducts() {
  allProducts = await apiFetch("/products?store_id=1&active_only=false");
  const select = document.getElementById("tr-product");
  select.innerHTML = allProducts
    .map((p) => `<option value="${p.id}">${escapeHtml(p.name)} (${escapeHtml(p.sku)})</option>`)
    .join("");
}

async function loadStores() {
  try {
    stores = await apiFetch("/stores");
  } catch (err) {
    showToast(err.message, "error");
    return;
  }
  if (stores.length < 2) {
    document.querySelector(".page").insertAdjacentHTML(
      "afterbegin",
      `<div class="empty-state" style="background:#fff; border:1px solid var(--border); border-radius:10px; margin-bottom:16px;">
        You need at least two stores to transfer stock. Add another store on the <a href="stores.html">Stores</a> page first.
      </div>`
    );
  }
  const options = stores.map((s) => `<option value="${s.id}">${escapeHtml(s.name)}</option>`).join("");
  document.getElementById("tr-from").innerHTML = options;
  document.getElementById("tr-to").innerHTML = options;
  if (stores.length > 1) {
    document.getElementById("tr-to").value = stores[1].id;
  }
}

function storeName(storeId) {
  const store = stores.find((s) => s.id === storeId);
  return store ? store.name : `#${storeId}`;
}

function productName(productId) {
  const product = allProducts.find((p) => p.id === productId);
  return product ? product.name : `#${productId}`;
}

async function loadHistory() {
  try {
    transfers = await apiFetch("/transfers?limit=100");
    renderHistory();
  } catch (err) {
    showToast(err.message, "error");
  }
}

function renderHistory() {
  const tbody = document.getElementById("history-rows");
  const emptyState = document.getElementById("empty-state");

  if (transfers.length === 0) {
    tbody.innerHTML = "";
    emptyState.style.display = "block";
    return;
  }
  emptyState.style.display = "none";

  tbody.innerHTML = transfers
    .map(
      (t) => `
        <tr>
          <td>${formatDate(t.created_at)}</td>
          <td>${escapeHtml(productName(t.product_id))}</td>
          <td>${escapeHtml(storeName(t.from_store_id))}</td>
          <td>${escapeHtml(storeName(t.to_store_id))}</td>
          <td>${t.qty}</td>
          <td>${escapeHtml(t.note || "—")}</td>
        </tr>
      `
    )
    .join("");
}

async function updateAvailable() {
  const productId = parseInt(document.getElementById("tr-product").value, 10);
  const fromStoreId = parseInt(document.getElementById("tr-from").value, 10);
  const box = document.getElementById("tr-available");
  if (!productId || !fromStoreId) {
    box.textContent = "";
    return;
  }
  try {
    const rows = await apiFetch(`/inventory?store_id=${fromStoreId}`);
    const row = rows.find((r) => r.product_id === productId);
    box.textContent = `Available at ${storeName(fromStoreId)}: ${row ? row.quantity : 0}`;
  } catch (err) {
    box.textContent = "";
  }
}

function wireEvents() {
  document.getElementById("tr-product").addEventListener("change", updateAvailable);
  document.getElementById("tr-from").addEventListener("change", updateAvailable);
  document.getElementById("transfer-form").addEventListener("submit", submitTransfer);
}

async function submitTransfer(e) {
  e.preventDefault();
  const payload = {
    product_id: parseInt(document.getElementById("tr-product").value, 10),
    from_store_id: parseInt(document.getElementById("tr-from").value, 10),
    to_store_id: parseInt(document.getElementById("tr-to").value, 10),
    qty: parseInt(document.getElementById("tr-qty").value, 10),
    note: document.getElementById("tr-note").value.trim() || null,
  };

  if (payload.from_store_id === payload.to_store_id) {
    showToast("From and to stores must be different", "error");
    return;
  }

  try {
    await apiFetch("/transfers", { method: "POST", body: JSON.stringify(payload) });
    showToast("Stock transferred");
    document.getElementById("tr-qty").value = "";
    document.getElementById("tr-note").value = "";
    await loadHistory();
    await updateAvailable();
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
