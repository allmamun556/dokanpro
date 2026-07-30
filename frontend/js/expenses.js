let expenses = [];

async function init() {
  const user = await renderNav("expenses.html");
  if (!hasPermission(user, "expenses.manage")) {
    document.querySelector(".page").innerHTML = `<div class="empty-state">You do not have permission to manage expenses.</div>`;
    return;
  }
  document.getElementById("expense-form").addEventListener("submit", submitExpense);
  document.getElementById("filter-from").addEventListener("change", loadExpenses);
  document.getElementById("filter-to").addEventListener("change", loadExpenses);
  await loadExpenses();
}

function queryParams() {
  const from = document.getElementById("filter-from").value;
  const to = document.getElementById("filter-to").value;
  const params = new URLSearchParams({ store_id: "1" });
  if (from) params.set("date_from", from);
  if (to) params.set("date_to", to);
  return params.toString();
}

async function loadExpenses() {
  try {
    const qs = queryParams();
    const [rows, totalResp] = await Promise.all([
      apiFetch(`/expenses?${qs}`),
      apiFetch(`/expenses/total?${qs}`),
    ]);
    expenses = rows;
    document.getElementById("stat-total").textContent = formatMoney(totalResp.total);
    renderTable();
  } catch (err) {
    showToast(err.message, "error");
  }
}

function renderTable() {
  const tbody = document.getElementById("expense-rows");
  const emptyState = document.getElementById("empty-state");

  if (expenses.length === 0) {
    tbody.innerHTML = "";
    emptyState.style.display = "block";
    return;
  }
  emptyState.style.display = "none";

  tbody.innerHTML = expenses
    .map(
      (e) => `
        <tr>
          <td>${e.expense_date}</td>
          <td>${escapeHtml(e.category)}</td>
          <td>${escapeHtml(e.description || "—")}</td>
          <td>${formatMoney(e.amount)}</td>
          <td><button class="btn btn-danger btn-sm" onclick="deleteExpense(${e.id})">Delete</button></td>
        </tr>
      `
    )
    .join("");
}

function openExpenseModal() {
  document.getElementById("ex-category").value = "";
  document.getElementById("ex-amount").value = "";
  document.getElementById("ex-date").value = new Date().toISOString().slice(0, 10);
  document.getElementById("ex-description").value = "";
  document.getElementById("expense-modal").style.display = "flex";
}

function closeExpenseModal() {
  document.getElementById("expense-modal").style.display = "none";
  document.getElementById("expense-form").reset();
}

async function submitExpense(e) {
  e.preventDefault();
  const payload = {
    store_id: 1,
    category: document.getElementById("ex-category").value.trim(),
    amount: parseFloat(document.getElementById("ex-amount").value),
    expense_date: document.getElementById("ex-date").value,
    description: document.getElementById("ex-description").value.trim() || null,
  };

  try {
    await apiFetch("/expenses", { method: "POST", body: JSON.stringify(payload) });
    showToast("Expense recorded");
    closeExpenseModal();
    await loadExpenses();
  } catch (err) {
    showToast(err.message, "error");
  }
}

async function deleteExpense(expenseId) {
  try {
    await apiFetch(`/expenses/${expenseId}`, { method: "DELETE" });
    showToast("Expense deleted");
    await loadExpenses();
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
