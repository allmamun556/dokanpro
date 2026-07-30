let stores = [];

async function init() {
  const user = await renderNav("stores.html");
  if (!hasPermission(user, "stores.manage")) {
    document.querySelector(".page").innerHTML = `<div class="empty-state">You do not have permission to manage stores.</div>`;
    return;
  }
  await loadStores();
  document.getElementById("store-form").addEventListener("submit", submitStore);
}

async function loadStores() {
  try {
    stores = await apiFetch("/stores");
    renderTable();
  } catch (err) {
    showToast(err.message, "error");
  }
}

function renderTable() {
  const tbody = document.getElementById("store-rows");
  const emptyState = document.getElementById("empty-state");

  if (stores.length === 0) {
    tbody.innerHTML = "";
    emptyState.style.display = "block";
    return;
  }
  emptyState.style.display = "none";

  tbody.innerHTML = stores
    .map(
      (s) => `
        <tr>
          <td>${escapeHtml(s.name)}</td>
          <td>${escapeHtml(s.address || "—")}</td>
          <td><button class="btn btn-secondary btn-sm" onclick='openStoreModal(${JSON.stringify(s).replace(/'/g, "&#39;")})'>Edit</button></td>
        </tr>
      `
    )
    .join("");
}

function openStoreModal(store = null) {
  document.getElementById("modal-title").textContent = store ? "Edit Store" : "New Store";
  document.getElementById("st-id").value = store ? store.id : "";
  document.getElementById("st-name").value = store ? store.name : "";
  document.getElementById("st-address").value = store ? store.address || "" : "";
  document.getElementById("store-modal").style.display = "flex";
}

function closeStoreModal() {
  document.getElementById("store-modal").style.display = "none";
  document.getElementById("store-form").reset();
}

async function submitStore(e) {
  e.preventDefault();
  const id = document.getElementById("st-id").value;
  const payload = {
    name: document.getElementById("st-name").value.trim(),
    address: document.getElementById("st-address").value.trim() || null,
  };

  try {
    if (id) {
      await apiFetch(`/stores/${id}`, { method: "PATCH", body: JSON.stringify(payload) });
      showToast("Store updated");
    } else {
      await apiFetch("/stores", { method: "POST", body: JSON.stringify(payload) });
      showToast("Store created");
    }
    closeStoreModal();
    await loadStores();
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
