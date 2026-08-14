let users = [];
let permissionsCatalog = [];
let currentUser = null;

async function init() {
  currentUser = await renderNav("users.html");
  if (!hasPermission(currentUser, "users.manage")) {
    document.querySelector(".page").innerHTML = `<div class="empty-state">You do not have permission to manage users.</div>`;
    return;
  }
  await loadPermissionsCatalog();
  await loadUsers();
  document.getElementById("user-form").addEventListener("submit", submitUser);
  document.getElementById("u-role").addEventListener("change", _onRoleChange);
}

async function loadPermissionsCatalog() {
  try {
    permissionsCatalog = await apiFetch("/users/permissions");
  } catch (err) {
    // Non-critical: permission overrides section just won't render
  }
}

async function loadUsers() {
  try {
    users = await apiFetch("/users");
    renderTable();
  } catch (err) {
    showToast(err.message, "error");
  }
}

function renderTable() {
  const tbody = document.getElementById("user-rows");
  const emptyState = document.getElementById("empty-state");

  if (users.length === 0) {
    tbody.innerHTML = "";
    emptyState.style.display = "block";
    return;
  }
  emptyState.style.display = "none";

  tbody.innerHTML = users
    .map(
      (u) => `
        <tr>
          <td>${escapeHtml(u.name)}</td>
          <td>${escapeHtml(u.email)}</td>
          <td><span class="badge badge-role">${u.role}</span></td>
          <td>${escapeHtml(u.position || "—")}</td>
          <td>${escapeHtml(u.phone || "—")}</td>
          <td><span class="badge ${u.is_active ? "badge-ok" : "badge-low"}">${u.is_active ? "Active" : "Disabled"}</span></td>
          <td>${formatDate(u.created_at)}</td>
          <td>
            <button class="btn btn-secondary btn-sm" onclick='openUserModal(${JSON.stringify(u).replace(/'/g, "&#39;")})'>Edit</button>
            <button class="btn ${u.is_active ? "btn-danger" : "btn-success"} btn-sm" onclick="toggleActive(${u.id}, ${!u.is_active})">${u.is_active ? "Disable" : "Enable"}</button>
          </td>
        </tr>
      `
    )
    .join("");
}

function openUserModal(user = null) {
  document.getElementById("modal-title").textContent = user ? "Edit User" : "New User";
  document.getElementById("u-id").value = user ? user.id : "";
  document.getElementById("u-name").value = user ? user.name : "";
  document.getElementById("u-email").value = user ? user.email : "";
  document.getElementById("u-password").value = "";
  document.getElementById("password-hint").textContent = user ? "" : "(required for new users)";
  document.getElementById("u-password").required = !user;
  document.getElementById("u-role").value = user ? user.role : "cashier";
  document.getElementById("u-phone").value = user ? user.phone || "" : "";
  document.getElementById("u-position").value = user ? user.position || "" : "";
  document.getElementById("u-hire-date").value = user ? user.hire_date || "" : "";
  document.getElementById("u-salary").value = user && user.salary != null ? user.salary : "";
  document.getElementById("active-row").style.display = user ? "block" : "none";
  document.getElementById("u-active").checked = user ? user.is_active : true;

  // Email cannot be changed after creation (kept simple / matches backend schema)
  document.getElementById("u-email").disabled = !!user;

  const permsSection = document.getElementById("permissions-section");
  if (permissionsCatalog.length > 0) {
    permsSection.style.display = "block";
    const overrides = user ? user.permission_overrides || {} : {};
    renderPermissionsList(overrides);
  } else {
    permsSection.style.display = "none";
  }

  document.getElementById("user-modal").style.display = "flex";
}

// What "Default" resolves to for the role currently selected in the form —
// recomputed on every render so switching roles updates the hint live.
function _defaultLabelFor(permKey) {
  const role = document.getElementById("u-role").value;
  const allowed = role === "admin" ? true : !!(ROLE_PERMISSION_DEFAULTS[role] || {})[permKey];
  return allowed ? "Default (Allowed)" : "Default (Denied)";
}

function renderPermissionsList(overrides) {
  document.getElementById("permissions-list").innerHTML = permissionsCatalog
    .map((p) => {
      const current = p.key in overrides ? (overrides[p.key] ? "allow" : "deny") : "default";
      return `
        <div class="form-row" style="align-items:center; margin-bottom:6px;">
          <div style="flex:2;">
            <div style="font-weight:600; font-size:13px;">${escapeHtml(p.label)}</div>
            <div style="font-size:11px; color:var(--text-muted);">${escapeHtml(p.description)}</div>
          </div>
          <div style="flex:1;">
            <select data-perm-key="${p.key}" style="margin:0;">
              <option value="default" ${current === "default" ? "selected" : ""}>${_defaultLabelFor(p.key)}</option>
              <option value="allow" ${current === "allow" ? "selected" : ""}>Allow</option>
              <option value="deny" ${current === "deny" ? "selected" : ""}>Deny</option>
            </select>
          </div>
        </div>
      `;
    })
    .join("");
}

// Re-label each "Default" option when the base role changes, without
// discarding any explicit Allow/Deny choices already made.
function _onRoleChange() {
  const overrides = {};
  document.querySelectorAll("#permissions-list select[data-perm-key]").forEach((select) => {
    if (select.value === "allow") overrides[select.dataset.permKey] = true;
    else if (select.value === "deny") overrides[select.dataset.permKey] = false;
  });
  if (permissionsCatalog.length > 0) renderPermissionsList(overrides);
}

function closeUserModal() {
  document.getElementById("user-modal").style.display = "none";
  document.getElementById("user-form").reset();
  document.getElementById("u-email").disabled = false;
}

async function submitUser(e) {
  e.preventDefault();
  const id = document.getElementById("u-id").value;
  const password = document.getElementById("u-password").value;

  const profileFields = {
    phone: document.getElementById("u-phone").value.trim() || null,
    position: document.getElementById("u-position").value.trim() || null,
    hire_date: document.getElementById("u-hire-date").value || null,
    salary: document.getElementById("u-salary").value ? parseFloat(document.getElementById("u-salary").value) : null,
  };

  const permission_overrides = {};
  document.querySelectorAll("#permissions-list select[data-perm-key]").forEach((select) => {
    if (select.value === "allow") permission_overrides[select.dataset.permKey] = true;
    else if (select.value === "deny") permission_overrides[select.dataset.permKey] = false;
  });

  try {
    if (id) {
      const payload = Object.assign(
        {
          name: document.getElementById("u-name").value.trim(),
          role: document.getElementById("u-role").value,
          is_active: document.getElementById("u-active").checked,
          permission_overrides,
        },
        profileFields
      );
      if (password) payload.password = password;
      await apiFetch(`/users/${id}`, { method: "PATCH", body: JSON.stringify(payload) });
      showToast("User updated");
    } else {
      const payload = Object.assign(
        {
          name: document.getElementById("u-name").value.trim(),
          email: document.getElementById("u-email").value.trim(),
          password,
          role: document.getElementById("u-role").value,
          permission_overrides,
        },
        profileFields
      );
      await apiFetch("/users", { method: "POST", body: JSON.stringify(payload) });
      showToast("User created");
    }
    closeUserModal();
    await loadUsers();
  } catch (err) {
    showToast(err.message, "error");
  }
}

async function toggleActive(userId, newState) {
  try {
    await apiFetch(`/users/${userId}`, { method: "PATCH", body: JSON.stringify({ is_active: newState }) });
    showToast(newState ? "User enabled" : "User disabled");
    await loadUsers();
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
