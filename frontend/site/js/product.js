function stars(rating) {
  const rounded = Math.round(rating);
  return "★".repeat(rounded) + "☆".repeat(5 - rounded);
}

function productIdFromQuery() {
  return new URLSearchParams(window.location.search).get("id");
}

async function init() {
  await renderSiteNav("product.html");
  renderSiteFooter();

  const productId = productIdFromQuery();
  if (!productId) {
    document.getElementById("product-card").innerHTML = `<div class="empty-state">No item specified.</div>`;
    return;
  }

  try {
    const item = await apiFetch(`/menu/products/${productId}`);
    renderProduct(item);
  } catch (err) {
    document.getElementById("product-card").innerHTML = `<div class="empty-state">Item not found.</div>`;
    return;
  }

  if (getToken()) {
    renderReviewForm(productId);
  } else {
    document.getElementById("review-form-container").innerHTML =
      `<p style="font-size:14px; color:var(--text-muted);"><a href="login.html">Log in</a> to leave a review (you must have ordered this item).</p>`;
  }

  await loadReviews(productId);
}

function renderProduct(item) {
  const meta = [];
  if (item.allergens) meta.push(`Allergens: ${escapeHtml(item.allergens)}`);
  if (item.calories) meta.push(`${item.calories} kcal`);

  document.getElementById("product-card").innerHTML = `
    <div style="display:flex; justify-content:space-between; align-items:baseline; font-size:24px; font-weight:700; margin-bottom:8px;">
      <span>${escapeHtml(item.name)}</span>
      <span class="price">${formatMoney(item.price)}</span>
    </div>
    ${item.avg_rating ? `<div style="color:var(--warning); margin-bottom:8px;">${stars(item.avg_rating)} ${item.avg_rating} (${item.review_count} review${item.review_count === 1 ? "" : "s"})</div>` : `<div style="color:var(--text-muted); margin-bottom:8px;">No reviews yet</div>`}
    ${item.description ? `<p>${escapeHtml(item.description)}</p>` : ""}
    ${meta.length ? `<p style="font-size:13px; color:var(--text-muted);">${meta.join(" &middot; ")}</p>` : ""}
    <button class="btn btn-accent" onclick='addItem(${JSON.stringify({ product_id: item.id, name: item.name, price: item.price }).replace(/'/g, "&#39;")})'>Add to Cart</button>
  `;
}

function addItem(item) {
  addToCart(item);
  showToast(`${item.name} added to cart`);
}

function renderReviewForm(productId) {
  document.getElementById("review-form-container").innerHTML = `
    <form id="review-form" style="margin-bottom:20px;">
      <label>Your rating</label>
      <select id="review-rating">
        <option value="5">★★★★★ (5)</option>
        <option value="4">★★★★☆ (4)</option>
        <option value="3">★★★☆☆ (3)</option>
        <option value="2">★★☆☆☆ (2)</option>
        <option value="1">★☆☆☆☆ (1)</option>
      </select>
      <label>Comment (optional)</label>
      <textarea id="review-comment" rows="3"></textarea>
      <button type="submit" class="btn btn-secondary" style="margin-top:8px;">Submit Review</button>
    </form>
  `;
  document.getElementById("review-form").addEventListener("submit", async (e) => {
    e.preventDefault();
    try {
      await apiFetch("/reviews", {
        method: "POST",
        body: JSON.stringify({
          product_id: parseInt(productId, 10),
          rating: parseInt(document.getElementById("review-rating").value, 10),
          comment: document.getElementById("review-comment").value.trim() || null,
        }),
      });
      showToast("Review submitted — thank you!");
      document.getElementById("review-form").reset();
      await loadReviews(productId);
    } catch (err) {
      showToast(err.message, "error");
    }
  });
}

async function loadReviews(productId) {
  try {
    const reviewList = await apiFetch(`/menu/products/${productId}/reviews`);
    const el = document.getElementById("reviews-list");
    el.innerHTML = reviewList.length
      ? reviewList
          .map(
            (r) => `
        <div class="cart-line" style="display:block;">
          <div style="display:flex; justify-content:space-between;">
            <strong>${escapeHtml(r.customer_name)}</strong>
            <span style="color:var(--warning);">${stars(r.rating)}</span>
          </div>
          ${r.comment ? `<p style="margin:6px 0 0;">${escapeHtml(r.comment)}</p>` : ""}
          ${r.admin_reply ? `<div style="background:var(--bg); border-radius:8px; padding:8px; margin-top:6px; font-size:13px;"><strong>Restaurant reply:</strong> ${escapeHtml(r.admin_reply)}</div>` : ""}
        </div>
      `
          )
          .join("")
      : `<div class="empty-state">No reviews yet — be the first!</div>`;
  } catch (err) {
    showToast(err.message, "error");
  }
}

init();
