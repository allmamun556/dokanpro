let suppliers = [];

async function init() {
  const user = await renderNav("suppliers.html");
  if (!hasPermission(user, "suppliers.manage")) {
    document.querySelector(".page").innerHTML = `<div class="empty-state">You do not have permission to manage suppliers.</div>`;
    return;
  }
  await loadSuppliers();
  document.getElementById("supplier-form").addEventListener("submit", submitSupplier);
}

async function loadSuppliers() {
  try {
    suppliers = await apiFetch("/suppliers");
    renderTable();
  } catch (err) {
    showToast(err.message, "error");
  }
}

function renderTable() {
  const tbody = document.getElementById("supplier-rows");
  const emptyState = document.getElementById("empty-state");

  if (suppliers.length === 0) {
    tbody.innerHTML = "";
    emptyState.style.display = "block";
    return;
  }
  emptyState.style.display = "none";

  tbody.innerHTML = suppliers
    .map(
      (s) => `
        <tr>
          <td>${escapeHtml(s.name)}</td>
          <td>${escapeHtml(s.phone || "—")}</td>
          <td>${escapeHtml(s.email || "—")}</td>
          <td>${escapeHtml(s.address || "—")}</td>
          <td>${s.total_due > 0.004 ? `<span class="badge badge-low">${formatMoney(s.total_due)}</span>` : `<span class="badge badge-ok">${formatMoney(0)}</span>`}</td>
          <td>
            <button class="btn btn-secondary btn-sm" onclick='openSupplierModal(${JSON.stringify(s).replace(/'/g, "&#39;")})'>Edit</button>
          </td>
        </tr>
      `
    )
    .join("");
}

function openSupplierModal(supplier = null) {
  document.getElementById("modal-title").textContent = supplier ? "Edit Supplier" : "New Supplier";
  document.getElementById("s-id").value = supplier ? supplier.id : "";
  document.getElementById("s-name").value = supplier ? supplier.name : "";
  document.getElementById("s-phone").value = supplier ? supplier.phone || "" : "";
  document.getElementById("s-email").value = supplier ? supplier.email || "" : "";
  document.getElementById("s-address").value = supplier ? supplier.address || "" : "";
  document.getElementById("supplier-modal").style.display = "flex";
}

function closeSupplierModal() {
  document.getElementById("supplier-modal").style.display = "none";
  document.getElementById("supplier-form").reset();
}

async function submitSupplier(e) {
  e.preventDefault();
  const id = document.getElementById("s-id").value;
  const payload = {
    name: document.getElementById("s-name").value.trim(),
    phone: document.getElementById("s-phone").value.trim() || null,
    email: document.getElementById("s-email").value.trim() || null,
    address: document.getElementById("s-address").value.trim() || null,
  };

  try {
    if (id) {
      await apiFetch(`/suppliers/${id}`, { method: "PATCH", body: JSON.stringify(payload) });
      showToast("Supplier updated");
    } else {
      await apiFetch("/suppliers", { method: "POST", body: JSON.stringify(payload) });
      showToast("Supplier created");
    }
    closeSupplierModal();
    await loadSuppliers();
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
