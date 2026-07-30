const API_BASE = window.location.origin + "/api/public";
const CURRENCY = "€";

// Multi-tenant: the site is served at both /site/... (single-tenant/dev) and
// /t/{slug}/site/... (multi-tenant). The API itself never moves — every
// call carries the slug as a header instead, resolved by the backend's
// tenant middleware. Reading it from the URL means no page needs to know
// its own tenant explicitly; it just follows wherever it's actually served from.
function getBusinessSlug() {
  const match = window.location.pathname.match(/^\/t\/([a-z0-9-]+)\//);
  return match ? match[1] : null;
}

if ("serviceWorker" in navigator) {
  window.addEventListener("load", () => {
    // Registered with a path relative to the current page, so it resolves to
    // /site/sw.js or /t/{slug}/site/sw.js depending on where the page is
    // served from — its default scope then naturally covers only that tenant.
    navigator.serviceWorker.register("sw.js").catch(() => {
      // Non-critical — the site works fine without offline support.
    });
  });
}

// --- Language (DE/EN toggle, static UI chrome only — see translations.js) ---

function getLang() {
  return localStorage.getItem("site_lang") || "de";
}

let _currentNavActiveHref = null;

function setLang(lang) {
  localStorage.setItem("site_lang", lang);
  applyTranslations();
  // The nav's own labels are built via t() at render time (not data-i18n),
  // since they depend on login state too — re-render it so it updates
  // in place instead of only taking effect after the next navigation.
  if (_currentNavActiveHref !== null) renderSiteNav(_currentNavActiveHref);
}

function t(key) {
  const dict = (typeof TRANSLATIONS !== "undefined" && TRANSLATIONS[getLang()]) || {};
  return dict[key] || key;
}

function applyTranslations() {
  document.querySelectorAll("[data-i18n]").forEach((el) => {
    el.textContent = t(el.getAttribute("data-i18n"));
  });
  document.querySelectorAll("[data-i18n-placeholder]").forEach((el) => {
    el.placeholder = t(el.getAttribute("data-i18n-placeholder"));
  });
}

function getToken() {
  return localStorage.getItem("site_customer_token");
}
function setToken(t) {
  localStorage.setItem("site_customer_token", t);
}
function clearToken() {
  localStorage.removeItem("site_customer_token");
}

async function apiFetch(path, options = {}) {
  const headers = Object.assign({}, options.headers || {});
  const token = getToken();
  if (token) headers["Authorization"] = `Bearer ${token}`;
  const slug = getBusinessSlug();
  if (slug) headers["X-Business-Slug"] = slug;
  if (options.body && !(options.body instanceof FormData)) {
    headers["Content-Type"] = "application/json";
  }

  const res = await fetch(`${API_BASE}${path}`, Object.assign({}, options, { headers }));

  if (res.status === 401) {
    clearToken();
  }

  if (!res.ok) {
    let detail = res.statusText;
    try {
      const body = await res.json();
      detail = body.detail || detail;
    } catch (e) {}
    throw new Error(detail);
  }

  if (res.status === 204) return null;
  return res.json();
}

function requireCustomerAuth() {
  if (!getToken()) {
    window.location.href = "login.html";
  }
}

function logout() {
  clearToken();
  window.location.href = "index.html";
}

let _currentCustomer = null;
async function fetchCurrentCustomer() {
  if (_currentCustomer) return _currentCustomer;
  _currentCustomer = await apiFetch("/auth/me");
  return _currentCustomer;
}

function formatMoney(n) {
  return CURRENCY + Number(n).toFixed(2);
}

function formatDate(iso) {
  return new Date(iso).toLocaleString();
}

function showToast(message, type = "success") {
  const el = document.createElement("div");
  el.className = `toast ${type}`;
  el.textContent = message;
  document.body.appendChild(el);
  setTimeout(() => el.remove(), 3200);
}

function escapeHtml(str) {
  const div = document.createElement("div");
  div.textContent = str;
  return div.innerHTML;
}

async function downloadFile(path) {
  const token = getToken();
  const slug = getBusinessSlug();
  const headers = token ? { Authorization: `Bearer ${token}` } : {};
  if (slug) headers["X-Business-Slug"] = slug;
  const res = await fetch(`${API_BASE}${path}`, { headers });

  if (!res.ok) {
    let detail = res.statusText;
    try {
      const body = await res.json();
      detail = body.detail || detail;
    } catch (e) {}
    throw new Error(detail);
  }

  const blob = await res.blob();
  const disposition = res.headers.get("Content-Disposition") || "";
  const match = disposition.match(/filename="?([^"]+)"?/);
  const filename = match ? match[1] : "download";

  const url = URL.createObjectURL(blob);
  const a = document.createElement("a");
  a.href = url;
  a.download = filename;
  document.body.appendChild(a);
  a.click();
  a.remove();
  URL.revokeObjectURL(url);
}

// --- Cart (localStorage, guest or logged-in) -------------------------

function getCart() {
  try {
    return JSON.parse(localStorage.getItem("site_cart") || "[]");
  } catch (e) {
    return [];
  }
}

function saveCart(cart) {
  localStorage.setItem("site_cart", JSON.stringify(cart));
}

function addToCart(item) {
  const cart = getCart();
  const existing = cart.find((c) => c.product_id === item.product_id);
  if (existing) {
    existing.qty += 1;
  } else {
    cart.push({ product_id: item.product_id, name: item.name, price: item.price, qty: 1 });
  }
  saveCart(cart);
  updateCartBadge();
}

function updateCartQty(productId, qty) {
  let cart = getCart();
  if (qty <= 0) {
    cart = cart.filter((c) => c.product_id !== productId);
  } else {
    const item = cart.find((c) => c.product_id === productId);
    if (item) item.qty = qty;
  }
  saveCart(cart);
  updateCartBadge();
}

function clearCart() {
  saveCart([]);
  updateCartBadge();
}

function cartTotal() {
  return getCart().reduce((sum, c) => sum + c.price * c.qty, 0);
}

function setDineInTable(tableId, tableLabel) {
  localStorage.setItem("site_dine_in_table", JSON.stringify({ id: tableId, label: tableLabel || null }));
}

function getDineInTable() {
  try {
    return JSON.parse(localStorage.getItem("site_dine_in_table") || "null");
  } catch (e) {
    return null;
  }
}

function clearDineInTable() {
  localStorage.removeItem("site_dine_in_table");
}

function cartCount() {
  return getCart().reduce((sum, c) => sum + c.qty, 0);
}

function updateCartBadge() {
  const badge = document.getElementById("site-cart-count");
  if (badge) badge.textContent = cartCount();
}

// --- Nav ---------------------------------------------------------------

async function renderSiteNav(activeHref) {
  const container = document.getElementById("site-nav");
  if (!container) return;
  _currentNavActiveHref = activeHref;

  const token = getToken();
  let accountLink = `<a href="login.html">${t("nav.login")}</a>`;
  if (token) {
    try {
      await fetchCurrentCustomer();
      accountLink = `<a href="account.html">${t("nav.account")}</a> <a href="#" onclick="logout(); return false;">${t("nav.logout")}</a>`;
    } catch (e) {
      clearToken();
    }
  }

  const lang = getLang();
  const langToggle = `
    <span class="lang-toggle">
      <a href="#" onclick="setLang('de'); return false;" class="${lang === "de" ? "active" : ""}">DE</a> |
      <a href="#" onclick="setLang('en'); return false;" class="${lang === "en" ? "active" : ""}">EN</a>
    </span>
  `;

  container.innerHTML = `
    <div class="site-nav">
      <a href="index.html" class="brand">Bavaria <span>Genuss</span></a>
      <div class="links">
        <a href="index.html" class="${activeHref === "index.html" ? "active" : ""}">${t("nav.home")}</a>
        <a href="menu.html" class="${activeHref === "menu.html" ? "active" : ""}">${t("nav.menu")}</a>
        <a href="reservations.html" class="${activeHref === "reservations.html" ? "active" : ""}">${t("nav.reservations")}</a>
        ${accountLink}
        <a href="cart.html">${t("nav.cart")} <span class="cart-count" id="site-cart-count">${cartCount()}</span></a>
        ${langToggle}
      </div>
    </div>
  `;

  applyTranslations();
}

function renderSiteFooter() {
  const container = document.getElementById("site-footer");
  if (!container) return;
  container.innerHTML = `
    <div class="site-footer">
      <div style="max-width:360px; margin:0 auto 16px;">
        <form id="newsletter-form" style="display:flex; gap:8px;">
          <input type="email" id="newsletter-email" data-i18n-placeholder="footer.yourEmail" placeholder="Your email" required style="margin:0;" />
          <button type="submit" class="btn btn-accent btn-sm" data-i18n="footer.subscribe" style="white-space:nowrap;">Subscribe</button>
        </form>
        <div id="newsletter-feedback" style="font-size:12px; margin-top:6px;"></div>
      </div>
      Bavaria Genuss Restaurant &middot; Musterstraße 12, 80331 München &middot;
      <a href="impressum.html">Impressum</a> &middot;
      <a href="datenschutz.html">Datenschutz</a>
    </div>
  `;

  const form = document.getElementById("newsletter-form");
  if (form) {
    form.addEventListener("submit", async (e) => {
      e.preventDefault();
      const email = document.getElementById("newsletter-email").value.trim();
      const feedback = document.getElementById("newsletter-feedback");
      try {
        await apiFetch("/newsletter/subscribe", { method: "POST", body: JSON.stringify({ email }) });
        feedback.textContent = "Subscribed! Thanks for signing up.";
        feedback.style.color = "var(--success)";
        form.reset();
      } catch (err) {
        feedback.textContent = err.message;
        feedback.style.color = "var(--danger)";
      }
    });
  }

  applyTranslations();
}
