async function init() {
  await renderSiteNav("dine-in.html");
  renderSiteFooter();

  const tableId = new URLSearchParams(window.location.search).get("table_id");
  const card = document.getElementById("dine-in-card");

  if (!tableId) {
    card.innerHTML = `<div class="empty-state">No table specified. Please scan the QR code on your table.</div>`;
    return;
  }

  try {
    const table = await apiFetch(`/tables/${tableId}`);
    setDineInTable(table.id, table.label);
    card.innerHTML = `
      <h1>Table ${escapeHtml(table.label)}</h1>
      <p>You're ordering for this table. Anything you order will be sent straight to the kitchen.</p>
      <a href="menu.html" class="btn btn-accent btn-block" style="margin-top:16px;">Start Ordering</a>
    `;
  } catch (err) {
    card.innerHTML = `<div class="empty-state">This table code isn't valid. Please ask a member of staff for help.</div>`;
  }
}

function escapeHtml(str) {
  const div = document.createElement("div");
  div.textContent = str;
  return div.innerHTML;
}

init();
