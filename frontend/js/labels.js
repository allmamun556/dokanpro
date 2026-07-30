let allProducts = [];

async function init() {
  await renderNav("labels.html");
  await loadProducts();
  wireEvents();
}

async function loadProducts() {
  try {
    allProducts = await apiFetch("/products?store_id=1&active_only=true");
    renderTable(allProducts);
  } catch (err) {
    showToast(err.message, "error");
  }
}

function renderTable(products) {
  const tbody = document.getElementById("product-rows");
  const emptyState = document.getElementById("empty-state");

  if (products.length === 0) {
    tbody.innerHTML = "";
    emptyState.style.display = "block";
    return;
  }
  emptyState.style.display = "none";

  tbody.innerHTML = products
    .map(
      (p) => `
        <tr>
          <td>${escapeHtml(p.sku)}</td>
          <td>${escapeHtml(p.name)}</td>
          <td>${formatMoney(p.price)}</td>
          <td><input type="number" min="0" value="0" data-product-id="${p.id}" class="copies-input" style="margin:0; width:80px;" /></td>
        </tr>
      `
    )
    .join("");

  tbody.querySelectorAll(".copies-input").forEach((input) => {
    input.addEventListener("input", updatePrintButton);
  });
  updatePrintButton();
}

function updatePrintButton() {
  const total = Array.from(document.querySelectorAll(".copies-input")).reduce(
    (sum, input) => sum + (parseInt(input.value, 10) || 0),
    0
  );
  document.getElementById("print-btn").disabled = total === 0;
}

function wireEvents() {
  document.getElementById("search").addEventListener("input", (e) => {
    const term = e.target.value.toLowerCase();
    const filtered = allProducts.filter(
      (p) => p.name.toLowerCase().includes(term) || p.sku.toLowerCase().includes(term)
    );
    renderTable(filtered);
  });
}

function printLabels() {
  const printArea = document.getElementById("print-area");
  printArea.innerHTML = `<div class="label-grid" id="label-grid"></div>`;
  const grid = document.getElementById("label-grid");

  let labelIndex = 0;
  document.querySelectorAll(".copies-input").forEach((input) => {
    const copies = parseInt(input.value, 10) || 0;
    if (copies === 0) return;
    const productId = parseInt(input.dataset.productId, 10);
    const product = allProducts.find((p) => p.id === productId);
    if (!product) return;

    for (let i = 0; i < copies; i++) {
      labelIndex++;
      const svgId = `barcode-${labelIndex}`;
      const card = document.createElement("div");
      card.className = "label-card";
      card.innerHTML = `
        <div class="label-name">${escapeHtml(product.name)}</div>
        <svg id="${svgId}"></svg>
        <div class="label-price">${formatMoney(product.price)}</div>
      `;
      grid.appendChild(card);
      JsBarcode(`#${svgId}`, product.sku, {
        format: "CODE128",
        width: 1.5,
        height: 40,
        fontSize: 12,
        margin: 4,
      });
    }
  });

  window.print();
}

function escapeHtml(str) {
  const div = document.createElement("div");
  div.textContent = str;
  return div.innerHTML;
}

init();
