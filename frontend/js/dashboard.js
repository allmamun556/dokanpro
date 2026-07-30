let dailyChart = null;

async function init() {
  const user = await renderNav("dashboard.html");
  if (!hasPermission(user, "reports.profit")) {
    document.querySelector(".page").innerHTML = `<div class="empty-state">You do not have permission to view the dashboard.</div>`;
    return;
  }
  await load();
}

async function load() {
  try {
    const d = await apiFetch("/reports/dashboard?store_id=1");

    document.getElementById("stat-today").textContent = formatMoney(d.today_sales);
    document.getElementById("stat-today-orders").textContent = `${d.today_order_count} order(s)`;

    document.getElementById("stat-yesterday").textContent = formatMoney(d.yesterday_sales);
    document.getElementById("stat-yesterday-orders").textContent = `${d.yesterday_order_count} order(s)`;

    document.getElementById("stat-month").textContent = formatMoney(d.month_sales);
    document.getElementById("stat-month-orders").textContent = `${d.month_order_count} order(s)`;

    document.getElementById("stat-lowstock").textContent = d.low_stock_count;
    document.getElementById("stat-expiring").textContent = d.expiring_count;

    setProfitValue("stat-today-profit", d.today_profit);
    setProfitValue("stat-month-profit", d.month_profit);

    renderDailyChart(d.daily_sales);
    renderTopProducts(d.top_products);
  } catch (err) {
    showToast(err.message, "error");
  }
}

function setProfitValue(elementId, amount) {
  const el = document.getElementById(elementId);
  el.textContent = formatMoney(amount);
  el.style.color = amount < 0 ? "var(--danger)" : "";
}

function renderDailyChart(rows) {
  const ctx = document.getElementById("daily-sales-chart");
  const labels = rows.map((r) => r.day);
  const data = rows.map((r) => r.total);

  const gradient = ctx.getContext("2d").createLinearGradient(0, 0, 0, 220);
  gradient.addColorStop(0, "#c2410c");
  gradient.addColorStop(1, "#f97316");

  if (dailyChart) dailyChart.destroy();
  dailyChart = new Chart(ctx, {
    type: "bar",
    data: {
      labels,
      datasets: [{
        label: "Sales", data, backgroundColor: gradient,
        borderRadius: 6, maxBarThickness: 48,
      }],
    },
    options: {
      plugins: { legend: { display: false } },
      scales: {
        y: { beginAtZero: true, grid: { color: "#ece1d3" }, ticks: { color: "#8a7768" } },
        x: { grid: { display: false }, ticks: { color: "#8a7768" } },
      },
    },
  });
}

function renderTopProducts(rows) {
  const tbody = document.getElementById("top-products-rows");
  if (rows.length === 0) {
    tbody.innerHTML = `<tr><td colspan="3" class="empty-state">No sales in this period.</td></tr>`;
    return;
  }
  tbody.innerHTML = rows
    .map(
      (r) =>
        `<tr><td>${escapeHtml(r.name)}</td><td>${r.units_sold}</td><td>${formatMoney(r.revenue)}</td></tr>`
    )
    .join("");
}

function escapeHtml(str) {
  const div = document.createElement("div");
  div.textContent = str;
  return div.innerHTML;
}

init();
