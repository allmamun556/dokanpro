let currentUser = null;

async function init() {
  currentUser = await renderNav("settings.html");
  if (!hasPermission(currentUser, "settings.manage")) {
    document.querySelector(".page").innerHTML = `<div class="empty-state">You do not have permission to manage settings.</div>`;
    return;
  }
  document.getElementById("business-form").addEventListener("submit", submitBusinessSettings);
  document.getElementById("brand-form").addEventListener("submit", submitBrand);
  document.getElementById("unit-form").addEventListener("submit", submitUnit);
  document.getElementById("connect-btn").addEventListener("click", startStripeConnect);
  document.getElementById("subscribe-btn").addEventListener("click", startSubscribe);

  await Promise.all([loadBusinessSettings(), loadBrands(), loadUnits(), loadConnectStatus(), loadBillingStatus()]);
}

async function loadConnectStatus() {
  const statusEl = document.getElementById("connect-status");
  const btn = document.getElementById("connect-btn");
  try {
    const s = await apiFetch("/settings/stripe/connect/status");
    if (s.charges_enabled) {
      statusEl.textContent = "Connected — this business's own Stripe account receives diner payments.";
      btn.textContent = "Reconnect";
    } else if (s.connected) {
      statusEl.textContent = "Connected, but onboarding isn't finished yet — online ordering is disabled until it is.";
      btn.textContent = "Finish Connecting Stripe";
    } else {
      statusEl.textContent = "Not connected — online ordering is disabled until this is set up.";
      btn.textContent = "Connect Stripe";
    }
  } catch (err) {
    statusEl.textContent = err.message;
  }
}

async function startStripeConnect() {
  try {
    const { onboarding_url } = await apiFetch("/settings/stripe/connect", { method: "POST" });
    window.location.href = onboarding_url;
  } catch (err) {
    showToast(err.message, "error");
  }
}

async function loadBillingStatus() {
  const statusEl = document.getElementById("billing-status");
  const btn = document.getElementById("subscribe-btn");
  try {
    const s = await apiFetch("/billing/status");
    statusEl.textContent = s.subscribed ? `Active` : (s.status ? `Status: ${s.status}` : "Not subscribed");
    btn.style.display = s.subscribed ? "none" : "inline-block";
  } catch (err) {
    statusEl.textContent = err.message;
  }
}

async function startSubscribe() {
  try {
    const { checkout_url } = await apiFetch("/billing/subscribe", { method: "POST" });
    window.location.href = checkout_url;
  } catch (err) {
    showToast(err.message, "error");
  }
}

async function loadBusinessSettings() {
  try {
    const s = await apiFetch("/settings");
    document.getElementById("bs-name").value = s.business_name;
    document.getElementById("bs-currency").value = s.currency_symbol;
    document.getElementById("bs-address").value = s.address || "";
    document.getElementById("bs-vat").value = s.default_vat_rate;
    document.getElementById("bs-footer").value = s.receipt_footer || "";
  } catch (err) {
    showToast(err.message, "error");
  }
}

async function submitBusinessSettings(e) {
  e.preventDefault();
  const payload = {
    business_name: document.getElementById("bs-name").value.trim(),
    currency_symbol: document.getElementById("bs-currency").value.trim(),
    address: document.getElementById("bs-address").value.trim() || null,
    default_vat_rate: parseFloat(document.getElementById("bs-vat").value || "0"),
    receipt_footer: document.getElementById("bs-footer").value.trim() || null,
  };
  try {
    await apiFetch("/settings", { method: "PATCH", body: JSON.stringify(payload) });
    showToast("Business settings saved");
  } catch (err) {
    showToast(err.message, "error");
  }
}

async function loadBrands() {
  try {
    const brands = await apiFetch("/products/brands");
    const tbody = document.getElementById("brand-rows");
    const emptyState = document.getElementById("brand-empty");
    if (brands.length === 0) {
      tbody.innerHTML = "";
      emptyState.style.display = "block";
    } else {
      emptyState.style.display = "none";
      tbody.innerHTML = brands.map((b) => `<tr><td>${escapeHtml(b.name)}</td></tr>`).join("");
    }
  } catch (err) {
    showToast(err.message, "error");
  }
}

async function submitBrand(e) {
  e.preventDefault();
  const name = document.getElementById("brand-name").value.trim();
  if (!name) return;
  try {
    await apiFetch("/products/brands", { method: "POST", body: JSON.stringify({ name }) });
    document.getElementById("brand-name").value = "";
    showToast("Brand added");
    await loadBrands();
  } catch (err) {
    showToast(err.message, "error");
  }
}

async function loadUnits() {
  try {
    const units = await apiFetch("/products/units");
    const tbody = document.getElementById("unit-rows");
    const emptyState = document.getElementById("unit-empty");
    if (units.length === 0) {
      tbody.innerHTML = "";
      emptyState.style.display = "block";
    } else {
      emptyState.style.display = "none";
      tbody.innerHTML = units.map((u) => `<tr><td>${escapeHtml(u.name)}</td><td>${escapeHtml(u.abbreviation)}</td></tr>`).join("");
    }
  } catch (err) {
    showToast(err.message, "error");
  }
}

async function submitUnit(e) {
  e.preventDefault();
  const name = document.getElementById("unit-name").value.trim();
  const abbreviation = document.getElementById("unit-abbr").value.trim();
  if (!name || !abbreviation) return;
  try {
    await apiFetch("/products/units", { method: "POST", body: JSON.stringify({ name, abbreviation }) });
    document.getElementById("unit-name").value = "";
    document.getElementById("unit-abbr").value = "";
    showToast("Unit added");
    await loadUnits();
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
