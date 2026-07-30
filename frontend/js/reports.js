let dailyChart = null;
let topProductsChart = null;

async function init() {
  const user = await renderNav("reports.html");
  if (!hasPermission(user, "reports.profit")) {
    document.querySelector(".page").innerHTML = `<div class="empty-state">You do not have permission to view reports.</div>`;
    return;
  }
  document.getElementById("period-select").addEventListener("change", loadAll);
  await loadAll();
}

function getDays() {
  return parseInt(document.getElementById("period-select").value, 10);
}

async function loadAll() {
  const days = getDays();
  try {
    const [summary, daily, topProducts, byCashier, lowStock, profit, expiring] = await Promise.all([
      apiFetch(`/reports/summary?store_id=1&days=${days}`),
      apiFetch(`/reports/daily-sales?store_id=1&days=${days}`),
      apiFetch(`/reports/top-products?store_id=1&days=${days}&limit=8`),
      apiFetch(`/reports/sales-by-cashier?store_id=1&days=${days}`),
      apiFetch(`/reports/low-stock?store_id=1`),
      apiFetch(`/reports/profit?store_id=1&days=${days}`),
      apiFetch(`/reports/expiring?store_id=1&days=30`),
    ]);

    renderSummary(summary);
    renderDailyChart(daily);
    renderTopProductsChart(topProducts);
    renderCashierTable(byCashier);
    renderLowStockTable(lowStock);
    renderProfit(profit);
    renderExpiring(expiring);
  } catch (err) {
    showToast(err.message, "error");
  }
}

function renderSummary(s) {
  document.getElementById("stat-sales").textContent = formatMoney(s.total_sales);
  document.getElementById("stat-orders").textContent = s.order_count;
  document.getElementById("stat-aov").textContent = formatMoney(s.average_order_value);
  document.getElementById("stat-lowstock").textContent = s.low_stock_count;
}

function renderDailyChart(rows) {
  const ctx = document.getElementById("daily-sales-chart");
  const labels = rows.map((r) => r.day);
  const data = rows.map((r) => r.total);

  if (dailyChart) dailyChart.destroy();
  dailyChart = new Chart(ctx, {
    type: "bar",
    data: {
      labels,
      datasets: [{ label: "Sales", data, backgroundColor: "#2563eb" }],
    },
    options: {
      plugins: { legend: { display: false } },
      scales: { y: { beginAtZero: true } },
    },
  });
}

function renderTopProductsChart(rows) {
  const ctx = document.getElementById("top-products-chart");
  const labels = rows.map((r) => r.name);
  const data = rows.map((r) => r.units_sold);

  if (topProductsChart) topProductsChart.destroy();
  topProductsChart = new Chart(ctx, {
    type: "bar",
    data: {
      labels,
      datasets: [{ label: "Units sold", data, backgroundColor: "#16a34a" }],
    },
    options: {
      indexAxis: "y",
      plugins: { legend: { display: false } },
      scales: { x: { beginAtZero: true } },
    },
  });
}

function renderCashierTable(rows) {
  const tbody = document.getElementById("cashier-rows");
  if (rows.length === 0) {
    tbody.innerHTML = `<tr><td colspan="3" class="empty-state">No sales in this period.</td></tr>`;
    return;
  }
  tbody.innerHTML = rows
    .map((r) => `<tr><td>${escapeHtml(r.cashier)}</td><td>${r.order_count}</td><td>${formatMoney(r.total)}</td></tr>`)
    .join("");
}

function renderLowStockTable(rows) {
  const tbody = document.getElementById("lowstock-rows");
  if (rows.length === 0) {
    tbody.innerHTML = `<tr><td colspan="4" class="empty-state">All stock levels healthy.</td></tr>`;
    return;
  }
  tbody.innerHTML = rows
    .map(
      (r) =>
        `<tr><td>${escapeHtml(r.sku)}</td><td>${escapeHtml(r.name)}</td><td><span class="badge badge-low">${r.quantity}</span></td><td>${r.reorder_level}</td></tr>`
    )
    .join("");
}

function renderExpiring(rows) {
  const tbody = document.getElementById("expiring-rows");
  if (rows.length === 0) {
    tbody.innerHTML = `<tr><td colspan="5" class="empty-state">Nothing expiring in the next 30 days.</td></tr>`;
    return;
  }
  tbody.innerHTML = rows
    .map(
      (r) => `
        <tr>
          <td>${escapeHtml(r.sku)}</td>
          <td>${escapeHtml(r.name)}</td>
          <td>${r.expiry_date}</td>
          <td>${r.quantity}</td>
          <td>${r.is_expired ? `<span class="badge badge-low">Expired</span>` : `<span class="badge badge-warning">${r.days_until_expiry}d left</span>`}</td>
        </tr>
      `
    )
    .join("");
}

function renderProfit(b) {
  const rows = [
    ["Gross Sales", b.gross_sales, false],
    ["Discounts", -b.discounts, false],
    ["Refunds", -b.refunds, false],
    ["Net Revenue", b.net_revenue, true],
    ["Cost of Goods Sold", -b.cogs, false],
    ["Gross Profit", b.gross_profit, true],
    ["Expenses", -b.expenses, false],
    ["Net Profit", b.net_profit, true],
  ];
  document.getElementById("profit-rows").innerHTML = rows
    .map(
      ([label, amount, bold]) => `
        <tr style="${bold ? "font-weight:700;" : ""}">
          <td>${label}</td>
          <td style="${amount < 0 ? "color:var(--danger);" : ""}">${amount < 0 ? "-" : ""}${formatMoney(Math.abs(amount))}</td>
        </tr>
      `
    )
    .join("") + `<tr><td>Margin</td><td>${b.margin_pct.toFixed(1)}%</td></tr>`;
}

async function exportProfit(format) {
  toggleExportMenu("profit-export-menu");
  try {
    await downloadFile(`/reports/profit/export?format=${format}&store_id=1&days=${getDays()}`);
  } catch (err) {
    showToast(err.message, "error");
  }
}

async function exportExpiring(format) {
  toggleExportMenu("expiring-export-menu");
  try {
    await downloadFile(`/reports/expiring/export?format=${format}&store_id=1&days=30`);
  } catch (err) {
    showToast(err.message, "error");
  }
}

async function exportSales(format) {
  toggleExportMenu("sales-export-menu");
  try {
    await downloadFile(`/reports/daily-sales/export?format=${format}&store_id=1&days=${getDays()}`);
  } catch (err) {
    showToast(err.message, "error");
  }
}

async function exportLowStock(format) {
  toggleExportMenu("lowstock-export-menu");
  try {
    await downloadFile(`/reports/low-stock/export?format=${format}&store_id=1`);
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
