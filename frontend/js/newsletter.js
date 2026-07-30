let subscribers = [];

async function init() {
  const user = await renderNav("newsletter.html");
  if (!hasPermission(user, "customers.manage")) {
    document.querySelector(".page").innerHTML = `<div class="empty-state">You do not have permission to view the newsletter list.</div>`;
    return;
  }
  await loadSubscribers();
}

async function loadSubscribers() {
  try {
    subscribers = await apiFetch("/newsletter/subscribers");
    render();
  } catch (err) {
    showToast(err.message, "error");
  }
}

function render() {
  const tbody = document.getElementById("subscriber-rows");
  const emptyState = document.getElementById("empty-state");

  if (subscribers.length === 0) {
    tbody.innerHTML = "";
    emptyState.style.display = "block";
    return;
  }
  emptyState.style.display = "none";

  tbody.innerHTML = subscribers
    .map(
      (s) => `
        <tr>
          <td>${escapeHtml(s.email)}</td>
          <td><span class="badge ${s.is_subscribed ? "badge-ok" : "badge-low"}">${s.is_subscribed ? "Subscribed" : "Unsubscribed"}</span></td>
          <td>${formatDate(s.subscribed_at)}</td>
          <td><button class="btn btn-danger btn-sm" onclick="removeSubscriber(${s.id})">Delete</button></td>
        </tr>
      `
    )
    .join("");
}

async function removeSubscriber(id) {
  if (!confirm("Remove this subscriber?")) return;
  try {
    await apiFetch(`/newsletter/subscribers/${id}`, { method: "DELETE" });
    showToast("Subscriber removed");
    await loadSubscribers();
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
