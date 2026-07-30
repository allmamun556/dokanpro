let customers = [];

async function init() {
  const user = await renderNav("customers.html");
  if (!hasPermission(user, "customers.manage")) {
    document.querySelector(".page").innerHTML = `<div class="empty-state">You do not have permission to manage customers.</div>`;
    return;
  }
  await loadCustomers();
  document.getElementById("customer-form").addEventListener("submit", submitCustomer);
  document.getElementById("search").addEventListener("input", (e) => {
    const term = e.target.value.toLowerCase();
    const filtered = customers.filter(
      (c) => c.name.toLowerCase().includes(term) || (c.phone || "").toLowerCase().includes(term)
    );
    renderTable(filtered);
  });
}

async function loadCustomers() {
  try {
    customers = await apiFetch("/customers");
    renderTable(customers);
  } catch (err) {
    showToast(err.message, "error");
  }
}

function renderTable(rows) {
  const tbody = document.getElementById("customer-rows");
  const emptyState = document.getElementById("empty-state");

  if (rows.length === 0) {
    tbody.innerHTML = "";
    emptyState.style.display = "block";
    return;
  }
  emptyState.style.display = "none";

  tbody.innerHTML = rows
    .map(
      (c) => `
        <tr>
          <td>${escapeHtml(c.name)}</td>
          <td>${escapeHtml(c.phone || "—")}</td>
          <td>${escapeHtml(c.email || "—")}</td>
          <td>${c.loyalty_points}</td>
          <td>${formatMoney(c.total_spent)}</td>
          <td>${c.last_purchase ? formatDate(c.last_purchase) : "—"}</td>
          <td>
            <button class="btn btn-secondary btn-sm" onclick='openCustomerModal(${JSON.stringify(c).replace(/'/g, "&#39;")})'>Edit</button>
          </td>
        </tr>
      `
    )
    .join("");
}

function openCustomerModal(customer = null) {
  document.getElementById("modal-title").textContent = customer ? "Edit Customer" : "New Customer";
  document.getElementById("c-id").value = customer ? customer.id : "";
  document.getElementById("c-name").value = customer ? customer.name : "";
  document.getElementById("c-phone").value = customer ? customer.phone || "" : "";
  document.getElementById("c-email").value = customer ? customer.email || "" : "";
  document.getElementById("loyalty-row").style.display = customer ? "block" : "none";
  document.getElementById("c-loyalty").value = customer ? customer.loyalty_points : 0;
  document.getElementById("customer-modal").style.display = "flex";
}

function closeCustomerModal() {
  document.getElementById("customer-modal").style.display = "none";
  document.getElementById("customer-form").reset();
}

async function submitCustomer(e) {
  e.preventDefault();
  const id = document.getElementById("c-id").value;
  const payload = {
    name: document.getElementById("c-name").value.trim(),
    phone: document.getElementById("c-phone").value.trim() || null,
    email: document.getElementById("c-email").value.trim() || null,
  };

  try {
    if (id) {
      payload.loyalty_points = parseInt(document.getElementById("c-loyalty").value || "0", 10);
      await apiFetch(`/customers/${id}`, { method: "PATCH", body: JSON.stringify(payload) });
      showToast("Customer updated");
    } else {
      await apiFetch("/customers", { method: "POST", body: JSON.stringify(payload) });
      showToast("Customer created");
    }
    closeCustomerModal();
    await loadCustomers();
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
