async function init() {
  await renderSiteNav("menu.html");
  renderSiteFooter();

  try {
    const categories = await apiFetch("/menu");
    render(categories);
  } catch (err) {
    document.getElementById("menu-container").innerHTML =
      `<div class="empty-state">Could not load the menu right now.</div>`;
  }
}

function render(categories) {
  const container = document.getElementById("menu-container");

  if (categories.length === 0) {
    container.innerHTML = `<div class="empty-state">Nothing on the menu yet — check back soon.</div>`;
    return;
  }

  container.innerHTML = categories
    .map(
      (cat) => `
      <div class="menu-category">
        <h2>${escapeHtml(cat.name)}</h2>
        <div class="menu-items">
          ${cat.items.map(itemCardHtml).join("")}
        </div>
      </div>
    `
    )
    .join("");
}

function itemCardHtml(item) {
  const meta = [];
  if (item.allergens) meta.push(`Allergens: ${escapeHtml(item.allergens)}`);
  if (item.calories) meta.push(`${item.calories} kcal`);

  const ratingHtml = item.avg_rating
    ? `★ ${item.avg_rating} (${item.review_count})`
    : "No reviews yet";

  return `
    <div class="menu-item-card">
      <div class="name-row">
        <span>${escapeHtml(item.name)}</span>
        <span class="price">${formatMoney(item.price)}</span>
      </div>
      <div class="meta"><a href="product.html?id=${item.id}">${ratingHtml} · Details &amp; Reviews</a></div>
      ${item.description ? `<div class="desc">${escapeHtml(item.description)}</div>` : ""}
      ${meta.length ? `<div class="meta">${meta.join(" &middot; ")}</div>` : ""}
      <button class="btn btn-accent btn-sm" onclick='addItem(${JSON.stringify({ product_id: item.id, name: item.name, price: item.price }).replace(/'/g, "&#39;")})'>
        Add to Cart
      </button>
    </div>
  `;
}

function addItem(item) {
  addToCart(item);
  showToast(`${item.name} added to cart`);
}

init();
