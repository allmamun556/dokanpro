async function init() {
  await renderSiteNav("index.html");
  renderSiteFooter();
  await loadRecommendations();
}

async function loadRecommendations() {
  try {
    const result = await apiFetch("/recommendations");
    if (!result.items || result.items.length === 0) return;

    document.getElementById("recommendations-section").style.display = "block";
    document.getElementById("recommendations-items").innerHTML = result.items
      .map(
        (item) => `
      <div class="menu-item-card">
        <div class="name-row">
          <span>${escapeHtml(item.name)}</span>
          <span class="price">${formatMoney(item.price)}</span>
        </div>
        <div class="desc">${escapeHtml(item.reason)}</div>
        <button class="btn btn-accent btn-sm" onclick='addItem(${JSON.stringify({ product_id: item.product_id, name: item.name, price: item.price }).replace(/'/g, "&#39;")})'>
          Add to Cart
        </button>
      </div>
    `
      )
      .join("");
  } catch (err) {
    // Non-critical — recommendations failing shouldn't break the home page.
  }
}

function addItem(item) {
  addToCart(item);
  showToast(`${item.name} added to cart`);
}

init();
