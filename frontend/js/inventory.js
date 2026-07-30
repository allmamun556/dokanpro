let categories = [];
let brands = [];
let units = [];
let inventoryRows = [];
let currentFilter = "all";
let currentUser = null;

async function init() {
  currentUser = await renderNav("inventory.html");
  await Promise.all([loadCategories(), loadBrands(), loadUnits()]);
  await loadData();
  wireEvents();
}

async function loadCategories() {
  try {
    categories = await apiFetch("/products/categories");
    const select = document.getElementById("p-category");
    select.innerHTML =
      `<option value="">— none —</option>` +
      categories.map((c) => `<option value="${c.id}">${escapeHtml(c.name)}</option>`).join("");
  } catch (err) {
    showToast(err.message, "error");
  }
}

async function loadBrands() {
  try {
    brands = await apiFetch("/products/brands");
    const select = document.getElementById("p-brand");
    select.innerHTML =
      `<option value="">— none —</option>` +
      brands.map((b) => `<option value="${b.id}">${escapeHtml(b.name)}</option>`).join("");
  } catch (err) {
    showToast(err.message, "error");
  }
}

async function loadUnits() {
  try {
    units = await apiFetch("/products/units");
    const select = document.getElementById("p-unit");
    select.innerHTML =
      `<option value="">— none —</option>` +
      units.map((u) => `<option value="${u.id}">${escapeHtml(u.name)} (${escapeHtml(u.abbreviation)})</option>`).join("");
  } catch (err) {
    showToast(err.message, "error");
  }
}

async function loadData() {
  try {
    if (currentFilter === "expiring") {
      const rows = await apiFetch("/reports/expiring?store_id=1&days=30");
      inventoryRows = rows.map((r) => ({
        product_id: r.product_id,
        sku: r.sku,
        product_name: r.name,
        quantity: r.quantity,
        reorder_level: null,
      }));
    } else {
      const path = currentFilter === "low" ? "/inventory/low-stock?store_id=1" : "/inventory?store_id=1";
      inventoryRows = await apiFetch(path);
    }
    renderTable();
  } catch (err) {
    showToast(err.message, "error");
  }
}

function expiryBadge(expiryDate) {
  if (!expiryDate) return "—";
  const days = Math.ceil((new Date(expiryDate) - new Date(new Date().toDateString())) / 86400000);
  if (days < 0) return `<span class="badge badge-low">Expired</span>`;
  if (days <= 30) return `<span class="badge badge-warning">${expiryDate} (${days}d)</span>`;
  return expiryDate;
}

function renderTable() {
  const tbody = document.getElementById("product-rows");
  const emptyState = document.getElementById("empty-state");

  if (inventoryRows.length === 0) {
    tbody.innerHTML = "";
    emptyState.style.display = "block";
    return;
  }
  emptyState.style.display = "none";

  // We need product price/tax/category/expiry too - fetch full product list once and merge
  tbody.innerHTML = inventoryRows
    .map((row) => {
      const low = row.reorder_level != null && row.quantity <= row.reorder_level;
      return `
        <tr>
          <td>—</td>
          <td>${escapeHtml(row.sku)}</td>
          <td>${escapeHtml(row.product_name)}</td>
          <td>—</td>
          <td>—</td>
          <td>—</td>
          <td>
            <span class="badge ${low ? "badge-low" : "badge-ok"}">${row.quantity}</span>
          </td>
          <td>${row.reorder_level != null ? row.reorder_level : "—"}</td>
          <td>—</td>
          <td>
            <button class="btn btn-secondary btn-sm" onclick="openAdjustModal(${row.product_id}, '${escapeHtml(row.product_name)}')">Adjust Stock</button>
          </td>
        </tr>
      `;
    })
    .join("");

  // Enrich with product details (price/tax/category) via a second call, non-blocking
  enrichRows();
}

async function enrichRows() {
  try {
    const products = await apiFetch("/products?store_id=1&active_only=false");
    const byId = {};
    products.forEach((p) => (byId[p.id] = p));

    const tbody = document.getElementById("product-rows");
    Array.from(tbody.querySelectorAll("tr")).forEach((tr, idx) => {
      const row = inventoryRows[idx];
      const p = byId[row.product_id];
      if (!p) return;
      const cells = tr.querySelectorAll("td");
      cells[0].innerHTML = p.image_url
        ? `<img src="${p.image_url}" style="width:40px; height:40px; object-fit:cover; border-radius:6px;" />`
        : `<div style="width:40px; height:40px; border-radius:6px; background:#f4f5f7; display:flex; align-items:center; justify-content:center; color:#9ca3af; font-size:16px;">—</div>`;
      const cat = categories.find((c) => c.id === p.category_id);
      cells[3].textContent = cat ? cat.name : "—";
      cells[4].textContent = formatMoney(p.price);
      cells[5].textContent = p.tax_rate + "%";
      cells[8].innerHTML = expiryBadge(p.expiry_date);
      // Add an edit button
      const actionsCell = cells[9];
      if (!actionsCell.querySelector(".edit-btn")) {
        const editBtn = document.createElement("button");
        editBtn.className = "btn btn-secondary btn-sm edit-btn";
        editBtn.style.marginLeft = "6px";
        editBtn.textContent = "Edit";
        editBtn.onclick = () => openProductModal(p);
        actionsCell.appendChild(editBtn);
      }
    });
  } catch (err) {
    // Non-critical, ignore
  }
}

function setFilter(filter) {
  currentFilter = filter;
  document.querySelectorAll(".tab").forEach((t) => t.classList.remove("active"));
  document.querySelector(`.tab[data-filter="${filter}"]`).classList.add("active");
  loadData();
}

function wireEvents() {
  document.getElementById("product-form").addEventListener("submit", submitProduct);
  document.getElementById("adjust-form").addEventListener("submit", submitAdjustment);
  document.getElementById("p-image-file").addEventListener("change", (e) => {
    const file = e.target.files[0];
    if (!file) return;
    const preview = document.getElementById("p-image-preview");
    preview.src = URL.createObjectURL(file);
    preview.style.display = "block";
  });
}

function openProductModal(product = null) {
  document.getElementById("modal-title").textContent = product ? "Edit Product" : "New Product";
  document.getElementById("p-id").value = product ? product.id : "";
  document.getElementById("p-sku").value = product ? product.sku : "";
  document.getElementById("p-name").value = product ? product.name : "";
  document.getElementById("p-category").value = product ? (product.category_id || "") : "";
  document.getElementById("p-brand").value = product ? (product.brand_id || "") : "";
  document.getElementById("p-unit").value = product ? (product.unit_id || "") : "";
  document.getElementById("p-price").value = product ? product.price : "";
  document.getElementById("p-cost").value = product ? product.cost : 0;
  document.getElementById("p-tax").value = product ? product.tax_rate : (_businessSettings ? _businessSettings.default_vat_rate : 0);
  document.getElementById("p-expiry").value = product ? product.expiry_date || "" : "";
  document.getElementById("p-description").value = product ? product.description || "" : "";
  document.getElementById("p-allergens").value = product ? product.allergens || "" : "";
  document.getElementById("p-calories").value = product ? product.calories || "" : "";
  document.getElementById("p-available-online").checked = product ? product.is_available_online : true;

  document.getElementById("p-image-file").value = "";
  const preview = document.getElementById("p-image-preview");
  const removeBtn = document.getElementById("p-image-remove-btn");
  if (product && product.image_url) {
    preview.src = product.image_url;
    preview.style.display = "block";
    removeBtn.style.display = "inline-flex";
  } else {
    preview.style.display = "none";
    removeBtn.style.display = "none";
  }

  // Initial stock fields only make sense for brand-new products
  document.getElementById("initial-stock-row").style.display = product ? "none" : "flex";

  document.getElementById("product-modal").style.display = "flex";
}

function closeProductModal() {
  document.getElementById("product-modal").style.display = "none";
  document.getElementById("product-form").reset();
  document.getElementById("p-image-preview").style.display = "none";
}

async function removeProductImage() {
  const id = document.getElementById("p-id").value;
  if (!id) return;
  try {
    await apiFetch(`/products/${id}/image`, { method: "DELETE" });
    document.getElementById("p-image-preview").style.display = "none";
    document.getElementById("p-image-remove-btn").style.display = "none";
    showToast("Image removed");
    await loadData();
  } catch (err) {
    showToast(err.message, "error");
  }
}

async function submitProduct(e) {
  e.preventDefault();
  const id = document.getElementById("p-id").value;
  const categoryVal = document.getElementById("p-category").value;
  const brandVal = document.getElementById("p-brand").value;
  const unitVal = document.getElementById("p-unit").value;

  const basePayload = {
    sku: document.getElementById("p-sku").value.trim(),
    name: document.getElementById("p-name").value.trim(),
    category_id: categoryVal ? parseInt(categoryVal, 10) : null,
    brand_id: brandVal ? parseInt(brandVal, 10) : null,
    unit_id: unitVal ? parseInt(unitVal, 10) : null,
    price: parseFloat(document.getElementById("p-price").value),
    cost: parseFloat(document.getElementById("p-cost").value || "0"),
    tax_rate: parseFloat(document.getElementById("p-tax").value || "0"),
    expiry_date: document.getElementById("p-expiry").value || null,
    description: document.getElementById("p-description").value.trim() || null,
    allergens: document.getElementById("p-allergens").value.trim() || null,
    calories: document.getElementById("p-calories").value ? parseInt(document.getElementById("p-calories").value, 10) : null,
    is_available_online: document.getElementById("p-available-online").checked,
  };

  const imageFile = document.getElementById("p-image-file").files[0];

  try {
    let productId = id ? parseInt(id, 10) : null;
    if (id) {
      await apiFetch(`/products/${id}`, { method: "PATCH", body: JSON.stringify(basePayload) });
      showToast("Product updated");
    } else {
      const payload = Object.assign({}, basePayload, {
        initial_quantity: parseInt(document.getElementById("p-initial-qty").value || "0", 10),
        reorder_level: parseInt(document.getElementById("p-reorder").value || "5", 10),
      });
      const created = await apiFetch("/products", { method: "POST", body: JSON.stringify(payload) });
      productId = created.id;
      showToast("Product created");
    }

    if (imageFile) {
      const formData = new FormData();
      formData.append("file", imageFile);
      await apiFetch(`/products/${productId}/image`, { method: "POST", body: formData });
    }

    closeProductModal();
    await loadData();
  } catch (err) {
    showToast(err.message, "error");
  }
}

function openAdjustModal(productId, productName) {
  document.getElementById("adjust-product-id").value = productId;
  document.getElementById("adjust-product-name").textContent = productName;
  document.getElementById("adjust-modal").style.display = "flex";
}

function closeAdjustModal() {
  document.getElementById("adjust-modal").style.display = "none";
  document.getElementById("adjust-form").reset();
}

async function submitAdjustment(e) {
  e.preventDefault();
  const productId = parseInt(document.getElementById("adjust-product-id").value, 10);
  const reason = document.getElementById("adjust-reason").value;
  const changeQty = parseInt(document.getElementById("adjust-qty").value, 10);
  const reference = document.getElementById("adjust-reference").value.trim() || null;

  try {
    await apiFetch("/inventory/adjust", {
      method: "POST",
      body: JSON.stringify({ product_id: productId, store_id: 1, change_qty: changeQty, reason, reference }),
    });
    showToast("Stock updated");
    closeAdjustModal();
    await loadData();
  } catch (err) {
    showToast(err.message, "error");
  }
}

async function exportInventory(format) {
  toggleExportMenu("inv-export-menu");
  try {
    await downloadFile(`/inventory/export?format=${format}&store_id=1`);
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
