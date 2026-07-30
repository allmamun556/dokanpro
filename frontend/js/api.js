const API_BASE = window.location.origin + "/api";

// Multi-tenant: staff pages are served at both /... (single-tenant/dev) and
// /t/{slug}/... (multi-tenant). The API never moves — every call carries the
// slug as a header instead, resolved by the backend's tenant middleware.
function getBusinessSlug() {
  const match = window.location.pathname.match(/^\/t\/([a-z0-9-]+)\//);
  return match ? match[1] : null;
}

function getToken() {
  return localStorage.getItem("pos_token");
}
function setToken(t) {
  localStorage.setItem("pos_token", t);
}
function clearToken() {
  localStorage.removeItem("pos_token");
}

// Opens a WebSocket to /ws/orders and calls onMessage() whenever an order is
// created or its fulfillment status changes. Auto-reconnects on drop (with a
// short backoff) but is purely an instant-refresh nicety — callers should
// keep their own polling as a fallback in case the socket never connects.
function connectOrdersWebSocket(onMessage) {
  const token = getToken();
  if (!token) return;
  const proto = window.location.protocol === "https:" ? "wss:" : "ws:";
  const ws = new WebSocket(`${proto}//${window.location.host}/ws/orders?token=${encodeURIComponent(token)}`);
  ws.onmessage = onMessage;
  ws.onclose = () => {
    setTimeout(() => connectOrdersWebSocket(onMessage), 5000);
  };
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
    window.location.href = "index.html";
    throw new Error("Session expired");
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

function requireAuth() {
  if (!getToken()) {
    window.location.href = "index.html";
  }
}

function logout() {
  clearToken();
  window.location.href = "index.html";
}

let _currentUser = null;
async function fetchCurrentUser() {
  if (_currentUser) return _currentUser;
  _currentUser = await apiFetch("/auth/me");
  return _currentUser;
}

// Mirrors backend/app/core/permissions.py ROLE_DEFAULTS — keep in sync.
const ROLE_PERMISSION_DEFAULTS = {
  manager: {
    "products.manage": true, "inventory.adjust": true, "discounts.manage": true,
    "customers.manage": true, "suppliers.manage": true, "purchases.manage": true,
    "transfers.manage": true, "expenses.manage": true, "stores.manage": true,
    "orders.refund": true, "reports.profit": true, "users.manage": false, "settings.manage": false,
    "orders.fulfill": true, "reservations.manage": true, "reviews.manage": true, "tables.manage": true,
  },
  cashier: { "orders.fulfill": true },
  waiter: { "orders.fulfill": true, "tables.manage": true },
  chef: { "orders.fulfill": true },
};

function hasPermission(user, key) {
  const overrides = user.permission_overrides || {};
  if (key in overrides) return !!overrides[key];
  if (user.role === "admin") return true;
  return !!(ROLE_PERMISSION_DEFAULTS[user.role] || {})[key];
}

function showToast(message, type = "success") {
  const el = document.createElement("div");
  el.className = `toast ${type}`;
  el.textContent = message;
  document.body.appendChild(el);
  setTimeout(() => el.remove(), 3200);
}

let _businessSettings = null;
async function fetchBusinessSettings() {
  if (_businessSettings) return _businessSettings;
  try {
    _businessSettings = await apiFetch("/settings");
  } catch (e) {
    _businessSettings = { business_name: "DokanPro", currency_symbol: "$", receipt_footer: "Thank you!" };
  }
  return _businessSettings;
}

function formatMoney(n) {
  const symbol = _businessSettings ? _businessSettings.currency_symbol : "$";
  return symbol + Number(n).toFixed(2);
}

function formatDate(iso) {
  const d = new Date(iso);
  return d.toLocaleString();
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
  const filename = match ? match[1] : "export";

  const url = URL.createObjectURL(blob);
  const a = document.createElement("a");
  a.href = url;
  a.download = filename;
  document.body.appendChild(a);
  a.click();
  a.remove();
  URL.revokeObjectURL(url);
}

function toggleExportMenu(id) {
  document.querySelectorAll(".export-menu, .notif-menu").forEach((el) => {
    if (el.id !== id) el.classList.remove("open");
  });
  document.getElementById(id).classList.toggle("open");
}

function toggleNotifMenu() {
  document.querySelectorAll(".export-menu, .notif-menu").forEach((el) => {
    if (el.id !== "notif-menu") el.classList.remove("open");
  });
  document.getElementById("notif-menu").classList.toggle("open");
}

document.addEventListener("click", (e) => {
  if (!e.target.closest(".export-dropdown")) {
    document.querySelectorAll(".export-menu").forEach((el) => el.classList.remove("open"));
  }
  if (!e.target.closest(".notif-dropdown")) {
    document.querySelectorAll(".notif-menu").forEach((el) => el.classList.remove("open"));
  }
  if (!e.target.closest(".nav-dropdown")) {
    document.querySelectorAll(".nav-dropdown-menu").forEach((el) => el.classList.remove("open"));
  }
});

function toggleNavMenu(id) {
  document.querySelectorAll(".nav-dropdown-menu").forEach((el) => {
    if (el.id !== id) el.classList.remove("open");
  });
  document.getElementById(id).classList.toggle("open");
}

function _escapeHtml(str) {
  const div = document.createElement("div");
  div.textContent = str;
  return div.innerHTML;
}

function _renderNotifList(elementId, rows, emptyMessage, rowHtmlFn) {
  const list = document.getElementById(elementId);
  if (!list) return;
  if (rows.length === 0) {
    list.innerHTML = `<div class="notif-empty">${emptyMessage}</div>`;
    return;
  }
  const shown = rows.slice(0, 8);
  list.innerHTML =
    shown.map(rowHtmlFn).join("") +
    (rows.length > shown.length ? `<div class="notif-more">+${rows.length - shown.length} more</div>` : "");
}

async function loadLowStockAlerts() {
  try {
    const [lowStock, expiring] = await Promise.all([
      apiFetch("/inventory/low-stock?store_id=1"),
      apiFetch("/reports/expiring?store_id=1&days=30"),
    ]);

    const badge = document.getElementById("notif-badge");
    if (!badge) return; // user already navigated away

    const total = lowStock.length + expiring.length;
    badge.style.display = total > 0 ? "flex" : "none";
    badge.textContent = total > 99 ? "99+" : total;

    _renderNotifList("notif-lowstock-list", lowStock, "All stock levels healthy.", (r) => `
      <div class="notif-item">
        <div>${_escapeHtml(r.product_name)}</div>
        <div class="notif-item-sub">${_escapeHtml(r.sku)} — ${r.quantity} left (reorder at ${r.reorder_level})</div>
      </div>
    `);

    _renderNotifList("notif-expiring-list", expiring, "Nothing expiring in the next 30 days.", (r) => `
      <div class="notif-item">
        <div>${_escapeHtml(r.name)}</div>
        <div class="notif-item-sub">${_escapeHtml(r.sku)} — ${r.is_expired ? "expired" : `${r.days_until_expiry}d left`} (${r.expiry_date})</div>
      </div>
    `);
  } catch (err) {
    // Non-critical, ignore
  }
}

// Flat top-level items keep quick one-click access for the most frequent
// actions; everything else groups into a dropdown by topic so the navbar
// doesn't have to lay all ~22 destinations out in a single unwrapping row.
const NAV_GROUPS = [
  { href: "dashboard.html", label: "Dashboard", permission: "reports.profit" },
  { href: "pos.html", label: "Checkout", roles: ["admin", "manager", "cashier", "waiter"] },
  {
    label: "Sales",
    items: [
      { href: "orders.html", label: "Orders", roles: ["admin", "manager", "cashier", "waiter"] },
      { href: "online-orders.html", label: "Online Orders", permission: "orders.fulfill" },
      { href: "kitchen-display.html", label: "Kitchen Display", permission: "orders.fulfill" },
      { href: "tables.html", label: "Tables", permission: "tables.manage" },
      { href: "reservations.html", label: "Reservations", permission: "reservations.manage" },
    ],
  },
  {
    label: "Inventory",
    items: [
      { href: "inventory.html", label: "Inventory", permission: "products.manage" },
      { href: "stock-history.html", label: "Stock History", roles: ["admin", "manager"] },
      { href: "labels.html", label: "Labels", roles: ["admin", "manager"] },
      { href: "purchases.html", label: "Purchases", permission: "purchases.manage" },
      { href: "suppliers.html", label: "Suppliers", permission: "suppliers.manage" },
      { href: "transfers.html", label: "Transfers", permission: "transfers.manage" },
    ],
  },
  {
    label: "Customers",
    items: [
      { href: "customers.html", label: "Customers", permission: "customers.manage" },
      { href: "newsletter.html", label: "Newsletter", permission: "customers.manage" },
      { href: "reviews.html", label: "Reviews", permission: "reviews.manage" },
      { href: "discounts.html", label: "Discounts", permission: "discounts.manage" },
    ],
  },
  { href: "reports.html", label: "Reports", permission: "reports.profit" },
  {
    label: "Admin",
    items: [
      { href: "stores.html", label: "Stores", permission: "stores.manage" },
      { href: "expenses.html", label: "Expenses", permission: "expenses.manage" },
      { href: "users.html", label: "Users", permission: "users.manage" },
      { href: "settings.html", label: "Settings", permission: "settings.manage" },
      { href: "notifications.html", label: "Notifications", permission: "settings.manage" },
    ],
  },
];

function _navItemVisible(item, user) {
  return item.permission ? hasPermission(user, item.permission) : item.roles.includes(user.role);
}

async function renderNav(activeHref) {
  requireAuth();
  const container = document.getElementById("nav");
  if (!container) return;

  let user;
  try {
    user = await fetchCurrentUser();
    await fetchBusinessSettings();
  } catch (e) {
    logout();
    return;
  }

  const links = NAV_GROUPS.map((entry, idx) => {
    if (entry.items) {
      const visible = entry.items.filter((item) => _navItemVisible(item, user));
      if (visible.length === 0) return "";
      const menuId = `nav-menu-${idx}`;
      const isActiveGroup = visible.some((item) => item.href === activeHref);
      const itemsHtml = visible
        .map((item) => `<a href="${item.href}" class="${item.href === activeHref ? "active" : ""}">${item.label}</a>`)
        .join("");
      return `
        <div class="nav-dropdown">
          <button type="button" class="nav-dropdown-trigger ${isActiveGroup ? "active" : ""}" onclick="toggleNavMenu('${menuId}')">
            ${entry.label} <span class="nav-dropdown-caret">&#9662;</span>
          </button>
          <div class="nav-dropdown-menu" id="${menuId}">${itemsHtml}</div>
        </div>
      `;
    }
    if (!_navItemVisible(entry, user)) return "";
    return `<a href="${entry.href}" class="${entry.href === activeHref ? "active" : ""}">${entry.label}</a>`;
  }).join("");

  const canSeeAlerts = ["admin", "manager"].includes(user.role);
  const bellHtml = canSeeAlerts
    ? `
    <div class="notif-dropdown">
      <button class="notif-bell" id="notif-bell" onclick="toggleNotifMenu()" title="Alerts">
        🔔<span class="notif-badge" id="notif-badge" style="display:none;"></span>
      </button>
      <div class="notif-menu" id="notif-menu">
        <div class="notif-header">Low Stock</div>
        <div id="notif-lowstock-list"><div class="notif-empty">Loading…</div></div>
        <div class="notif-header" style="border-top:1px solid var(--border);">Expiring Soon</div>
        <div id="notif-expiring-list"><div class="notif-empty">Loading…</div></div>
        <a href="inventory.html" class="notif-viewall">View Inventory →</a>
      </div>
    </div>
  `
    : "";

  const sectionLabel = { admin: "Admin Dashboard", manager: "Manager Dashboard", cashier: "Point of Sale", waiter: "Point of Sale", chef: "Kitchen" }[user.role] || "";

  container.innerHTML = `
    <div class="navbar">
      <div class="brand">
        <span class="brand-name">Dokan<span class="brand-accent">Pro</span></span>
        <span class="brand-subtitle">${sectionLabel}</span>
      </div>
      <div class="nav-links">${links}</div>
      <div class="nav-user">
        ${bellHtml}
        <span>${user.name}</span>
        <span class="role-badge">${user.role}</span>
        <button class="btn-logout" onclick="logout()">Log out</button>
      </div>
    </div>
  `;

  if (canSeeAlerts) loadLowStockAlerts();

  return user;
}
