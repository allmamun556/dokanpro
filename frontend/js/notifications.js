let notifications = [];

async function init() {
  const user = await renderNav("notifications.html");
  if (!hasPermission(user, "settings.manage")) {
    document.querySelector(".page").innerHTML = `<div class="empty-state">You do not have permission to view notifications.</div>`;
    return;
  }
  await loadNotifications();
}

async function loadNotifications() {
  try {
    notifications = await apiFetch("/notifications");
    render();
  } catch (err) {
    showToast(err.message, "error");
  }
}

function render() {
  const tbody = document.getElementById("notification-rows");
  const emptyState = document.getElementById("empty-state");

  if (notifications.length === 0) {
    tbody.innerHTML = "";
    emptyState.style.display = "block";
    return;
  }
  emptyState.style.display = "none";

  tbody.innerHTML = notifications
    .map(
      (n) => `
        <tr title="${escapeHtml(n.body)}">
          <td>${escapeHtml(n.event_type)}</td>
          <td>${escapeHtml(n.recipient_email || n.recipient_phone || "—")}</td>
          <td>${escapeHtml(n.subject)}</td>
          <td><span class="badge badge-warning">${escapeHtml(n.status)}</span></td>
          <td>${formatDate(n.created_at)}</td>
        </tr>
      `
    )
    .join("");
}

function escapeHtml(str) {
  const div = document.createElement("div");
  div.textContent = str;
  return div.innerHTML;
}

init();
