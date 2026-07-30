let allProducts = [];
let movements = [];

const REASON_LABELS = {
  sale: "Sale",
  refund: "Refund / Return",
  restock: "Manual Restock",
  adjustment: "Manual Adjustment",
  return_: "Return",
  purchase: "Purchase",
  purchase_return: "Purchase Return",
  transfer_in: "Transfer In",
  transfer_out: "Transfer Out",
};

async function init() {
  const user = await renderNav("stock-history.html");
  if (!["admin", "manager"].includes(user.role)) {
    document.querySelector(".page").innerHTML = `<div class="empty-state">Admins and managers only.</div>`;
    return;
  }
  await loadProducts();
  wireEvents();
  await loadMovements();
}

async function loadProducts() {
  try {
    allProducts = await apiFetch("/products?store_id=1&active_only=false");
    const select = document.getElementById("filter-product");
    select.innerHTML =
      `<option value="">All products</option>` +
      allProducts.map((p) => `<option value="${p.id}">${escapeHtml(p.name)} (${escapeHtml(p.sku)})</option>`).join("");
  } catch (err) {
    showToast(err.message, "error");
  }
}

function wireEvents() {
  document.getElementById("filter-product").addEventListener("change", loadMovements);
  document.getElementById("filter-reason").addEventListener("change", loadMovements);
}

function queryParams() {
  const params = new URLSearchParams({ store_id: "1", limit: "200" });
  const productId = document.getElementById("filter-product").value;
  const reason = document.getElementById("filter-reason").value;
  if (productId) params.set("product_id", productId);
  if (reason) params.set("reason", reason);
  return params.toString();
}

async function loadMovements() {
  try {
    movements = await apiFetch(`/inventory/movements?${queryParams()}`);
    renderTable();
  } catch (err) {
    showToast(err.message, "error");
  }
}

function renderTable() {
  const tbody = document.getElementById("movement-rows");
  const emptyState = document.getElementById("empty-state");

  if (movements.length === 0) {
    tbody.innerHTML = "";
    emptyState.style.display = "block";
    return;
  }
  emptyState.style.display = "none";

  tbody.innerHTML = movements
    .map(
      (m) => `
        <tr>
          <td>${formatDate(m.created_at)}</td>
          <td>${escapeHtml(m.product_name)} <span style="color:#6b7280;font-size:12px;">(${escapeHtml(m.sku)})</span></td>
          <td style="color:${m.change_qty >= 0 ? "var(--success)" : "var(--danger)"}; font-weight:600;">${m.change_qty >= 0 ? "+" : ""}${m.change_qty}</td>
          <td>${escapeHtml(REASON_LABELS[m.reason] || m.reason)}</td>
          <td>${escapeHtml(m.reference || "—")}</td>
          <td>${escapeHtml(m.created_by_name || "—")}</td>
        </tr>
      `
    )
    .join("");
}

async function exportMovements(format) {
  toggleExportMenu("history-export-menu");
  try {
    await downloadFile(`/inventory/movements/export?format=${format}&${queryParams()}`);
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
