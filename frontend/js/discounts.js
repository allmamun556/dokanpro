let discounts = [];

async function init() {
  const user = await renderNav("discounts.html");
  if (!hasPermission(user, "discounts.manage")) {
    document.querySelector(".page").innerHTML = `<div class="empty-state">You do not have permission to manage discounts.</div>`;
    return;
  }
  await loadDiscounts();
  document.getElementById("discount-form").addEventListener("submit", submitDiscount);
}

async function loadDiscounts() {
  try {
    discounts = await apiFetch("/discounts");
    renderTable();
  } catch (err) {
    showToast(err.message, "error");
  }
}

function formatWindow(d) {
  if (!d.starts_at && !d.ends_at) return "Always";
  const start = d.starts_at ? formatDate(d.starts_at) : "—";
  const end = d.ends_at ? formatDate(d.ends_at) : "—";
  return `${start} → ${end}`;
}

function formatValue(d) {
  return d.type === "percentage" ? `${d.value}%` : formatMoney(d.value);
}

function isExpired(d) {
  return d.ends_at && new Date(d.ends_at) < new Date();
}

function renderTable() {
  const tbody = document.getElementById("discount-rows");
  const emptyState = document.getElementById("empty-state");

  if (discounts.length === 0) {
    tbody.innerHTML = "";
    emptyState.style.display = "block";
    return;
  }
  emptyState.style.display = "none";

  tbody.innerHTML = discounts
    .map((d) => {
      const expired = isExpired(d);
      const statusLabel = !d.is_active ? "Disabled" : expired ? "Expired" : "Active";
      const statusClass = !d.is_active || expired ? "badge-low" : "badge-ok";
      return `
        <tr>
          <td><code>${escapeHtml(d.code)}</code></td>
          <td>${escapeHtml(d.name)}</td>
          <td>${d.type === "percentage" ? "Percentage" : "Fixed"}</td>
          <td>${formatValue(d)}</td>
          <td>${formatMoney(d.min_subtotal)}</td>
          <td style="font-size:12px;">${formatWindow(d)}</td>
          <td><span class="badge ${statusClass}">${statusLabel}</span></td>
          <td>
            <button class="btn btn-secondary btn-sm" onclick='openDiscountModal(${JSON.stringify(d).replace(/'/g, "&#39;")})'>Edit</button>
            <button class="btn ${d.is_active ? "btn-danger" : "btn-success"} btn-sm" onclick="toggleActive(${d.id}, ${!d.is_active})">${d.is_active ? "Disable" : "Enable"}</button>
          </td>
        </tr>
      `;
    })
    .join("");
}

function toIsoOrNull(localValue) {
  return localValue ? new Date(localValue).toISOString() : null;
}

function toLocalInputValue(iso) {
  if (!iso) return "";
  const d = new Date(iso);
  const pad = (n) => String(n).padStart(2, "0");
  return `${d.getFullYear()}-${pad(d.getMonth() + 1)}-${pad(d.getDate())}T${pad(d.getHours())}:${pad(d.getMinutes())}`;
}

function openDiscountModal(discount = null) {
  document.getElementById("modal-title").textContent = discount ? "Edit Discount" : "New Discount";
  document.getElementById("d-id").value = discount ? discount.id : "";
  document.getElementById("d-code").value = discount ? discount.code : "";
  document.getElementById("d-code").disabled = !!discount;
  document.getElementById("d-name").value = discount ? discount.name : "";
  document.getElementById("d-type").value = discount ? discount.type : "percentage";
  document.getElementById("d-value").value = discount ? discount.value : "";
  document.getElementById("d-min-subtotal").value = discount ? discount.min_subtotal : 0;
  document.getElementById("d-active").checked = discount ? discount.is_active : true;
  document.getElementById("d-starts-at").value = discount ? toLocalInputValue(discount.starts_at) : "";
  document.getElementById("d-ends-at").value = discount ? toLocalInputValue(discount.ends_at) : "";

  document.getElementById("discount-modal").style.display = "flex";
}

function closeDiscountModal() {
  document.getElementById("discount-modal").style.display = "none";
  document.getElementById("discount-form").reset();
  document.getElementById("d-code").disabled = false;
}

async function submitDiscount(e) {
  e.preventDefault();
  const id = document.getElementById("d-id").value;

  const commonPayload = {
    name: document.getElementById("d-name").value.trim(),
    type: document.getElementById("d-type").value,
    value: parseFloat(document.getElementById("d-value").value),
    min_subtotal: parseFloat(document.getElementById("d-min-subtotal").value || "0"),
    is_active: document.getElementById("d-active").checked,
    starts_at: toIsoOrNull(document.getElementById("d-starts-at").value),
    ends_at: toIsoOrNull(document.getElementById("d-ends-at").value),
  };

  try {
    if (id) {
      await apiFetch(`/discounts/${id}`, { method: "PATCH", body: JSON.stringify(commonPayload) });
      showToast("Discount updated");
    } else {
      const payload = Object.assign({ code: document.getElementById("d-code").value.trim() }, commonPayload);
      await apiFetch("/discounts", { method: "POST", body: JSON.stringify(payload) });
      showToast("Discount created");
    }
    closeDiscountModal();
    await loadDiscounts();
  } catch (err) {
    showToast(err.message, "error");
  }
}

async function toggleActive(discountId, newState) {
  try {
    await apiFetch(`/discounts/${discountId}`, { method: "PATCH", body: JSON.stringify({ is_active: newState }) });
    showToast(newState ? "Discount enabled" : "Discount disabled");
    await loadDiscounts();
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
