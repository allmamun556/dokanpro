let reviews = [];
let currentFilter = "all";
let replyingToId = null;

async function init() {
  const user = await renderNav("reviews.html");
  if (!hasPermission(user, "reviews.manage")) {
    document.querySelector(".page").innerHTML = `<div class="empty-state">You do not have permission to manage reviews.</div>`;
    return;
  }
  await loadReviews();
}

async function loadReviews() {
  try {
    const query = currentFilter === "unanswered" ? "?unanswered=true" : "";
    reviews = await apiFetch(`/reviews${query}`);
    render();
  } catch (err) {
    showToast(err.message, "error");
  }
}

function setFilter(filter) {
  currentFilter = filter;
  document.querySelectorAll(".tab").forEach((t) => t.classList.remove("active"));
  document.querySelector(`.tab[data-filter="${filter}"]`).classList.add("active");
  loadReviews();
}

function stars(rating) {
  return "★".repeat(rating) + "☆".repeat(5 - rating);
}

function render() {
  const list = document.getElementById("review-list");
  const emptyState = document.getElementById("empty-state");

  if (reviews.length === 0) {
    list.innerHTML = "";
    emptyState.style.display = "block";
    return;
  }
  emptyState.style.display = "none";

  list.innerHTML = reviews
    .map(
      (r) => `
    <div class="card" style="margin-bottom:12px;">
      <div style="display:flex; justify-content:space-between;">
        <div>
          <strong>${escapeHtml(r.customer_name)}</strong>
          <span style="color:var(--warning); margin-left:8px;">${stars(r.rating)}</span>
        </div>
        <span style="font-size:12px; color:var(--text-muted);">${formatDate(r.created_at)} &middot; Product #${r.product_id}</span>
      </div>
      ${r.comment ? `<p style="margin:10px 0;">${escapeHtml(r.comment)}</p>` : ""}
      ${
        r.admin_reply
          ? `<div style="background:var(--bg); border-radius:8px; padding:10px; margin-top:8px;">
               <strong style="font-size:13px;">Restaurant reply:</strong>
               <p style="margin:4px 0 0;">${escapeHtml(r.admin_reply)}</p>
             </div>`
          : `<button class="btn btn-secondary btn-sm" onclick="openReplyModal(${r.id})">Reply</button>`
      }
    </div>
  `
    )
    .join("");
}

function openReplyModal(id) {
  replyingToId = id;
  document.getElementById("reply-text").value = "";
  document.getElementById("reply-modal").style.display = "flex";
}

function closeReplyModal() {
  document.getElementById("reply-modal").style.display = "none";
  replyingToId = null;
}

async function submitReply() {
  const reply = document.getElementById("reply-text").value.trim();
  if (!reply) return;
  try {
    await apiFetch(`/reviews/${replyingToId}/reply`, { method: "POST", body: JSON.stringify({ reply }) });
    showToast("Reply sent");
    closeReplyModal();
    await loadReviews();
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
