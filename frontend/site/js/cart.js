let fulfillmentType = "pickup";
let currentCustomer = null;
let appliedCoupon = null; // { code, discount_amount }

const LOYALTY_REDEEM_POINTS = 100;
const LOYALTY_REDEEM_VALUE = 5;

async function init() {
  await renderSiteNav("cart.html");
  renderSiteFooter();

  if (getToken()) {
    document.getElementById("guest-fields").style.display = "none";
    try {
      currentCustomer = await fetchCurrentCustomer();
    } catch (e) {
      currentCustomer = null;
    }
  }

  const dineInTable = getDineInTable();
  if (dineInTable) {
    fulfillmentType = "dine_in";
    document.getElementById("checkout-form-title").textContent = "Table Order";
    const banner = document.getElementById("dine-in-banner");
    banner.style.display = "block";
    banner.textContent = `Ordering for Table ${dineInTable.label || dineInTable.id}`;
    document.getElementById("order-type-row").style.display = "none";
    document.getElementById("guest-fields").style.display = "none";
    document.getElementById("delivery-address-row").style.display = "none";
  }

  document.getElementById("coupon-row").style.display = "block";
  if (currentCustomer && currentCustomer.loyalty_points >= LOYALTY_REDEEM_POINTS) {
    document.getElementById("loyalty-row").style.display = "block";
    document.getElementById("loyalty-hint").textContent =
      `Redeem ${LOYALTY_REDEEM_POINTS} points for €${LOYALTY_REDEEM_VALUE.toFixed(2)} off (you have ${currentCustomer.loyalty_points})`;
  }

  render();
  document.getElementById("checkout-form").addEventListener("submit", submitCheckout);
}

function render() {
  const cart = getCart();
  const linesEl = document.getElementById("cart-lines");
  const emptyEl = document.getElementById("cart-empty");
  const totalRow = document.getElementById("cart-total-row");
  const formCard = document.getElementById("checkout-form-card");

  if (cart.length === 0) {
    linesEl.innerHTML = "";
    emptyEl.style.display = "block";
    totalRow.style.display = "none";
    formCard.style.display = "none";
    return;
  }
  emptyEl.style.display = "none";
  totalRow.style.display = "block";
  formCard.style.display = "block";

  linesEl.innerHTML = cart
    .map(
      (c) => `
      <div class="cart-line">
        <div>
          <div>${escapeHtml(c.name)}</div>
          <div style="font-size:12px; color:var(--text-muted);">${formatMoney(c.price)} each</div>
        </div>
        <div class="qty-controls">
          <button type="button" class="qty-btn" onclick="changeQty(${c.product_id}, ${c.qty - 1})">−</button>
          <span>${c.qty}</span>
          <button type="button" class="qty-btn" onclick="changeQty(${c.product_id}, ${c.qty + 1})">+</button>
          <span style="margin-left:12px; font-weight:600;">${formatMoney(c.price * c.qty)}</span>
        </div>
      </div>
    `
    )
    .join("");

  const subtotal = cartTotal();
  document.getElementById("cart-subtotal").textContent = formatMoney(subtotal);

  let running = subtotal;

  const couponRow = document.getElementById("coupon-discount-row");
  if (appliedCoupon) {
    couponRow.style.display = "flex";
    document.getElementById("coupon-discount").textContent = "−" + formatMoney(appliedCoupon.discount_amount);
    running -= appliedCoupon.discount_amount;
  } else {
    couponRow.style.display = "none";
  }

  const loyaltyRow = document.getElementById("loyalty-discount-row");
  const redeeming = document.getElementById("redeem-points") && document.getElementById("redeem-points").checked;
  if (redeeming) {
    const amount = Math.min(LOYALTY_REDEEM_VALUE, Math.max(0, running));
    loyaltyRow.style.display = "flex";
    document.getElementById("loyalty-discount").textContent = "−" + formatMoney(amount);
    running -= amount;
  } else {
    loyaltyRow.style.display = "none";
  }

  document.getElementById("cart-total").textContent = formatMoney(Math.max(0, running)) + " + tax";
}

function changeQty(productId, qty) {
  updateCartQty(productId, qty);
  render();
}

function setFulfillmentType(type) {
  fulfillmentType = type;
  document.querySelectorAll(".tab").forEach((t) => t.classList.toggle("active", t.dataset.type === type));
  document.getElementById("delivery-address-row").style.display = type === "delivery" ? "block" : "none";
}

async function applyCoupon() {
  const code = document.getElementById("coupon-code").value.trim();
  const feedback = document.getElementById("coupon-feedback");
  if (!code) return;

  try {
    const preview = await apiFetch(`/discounts/lookup/${encodeURIComponent(code)}?subtotal=${cartTotal()}`);
    appliedCoupon = { code: preview.code, discount_amount: preview.discount_amount };
    feedback.textContent = `Applied ${preview.code} — ${preview.name}`;
    feedback.style.color = "var(--success)";
    render();
  } catch (err) {
    appliedCoupon = null;
    feedback.textContent = err.message;
    feedback.style.color = "var(--danger)";
    render();
  }
}

async function submitCheckout(e) {
  e.preventDefault();
  const cart = getCart();
  if (cart.length === 0) return;

  const payload = {
    items: cart.map((c) => ({ product_id: c.product_id, qty: c.qty })),
    fulfillment_type: fulfillmentType,
  };

  if (appliedCoupon) payload.discount_code = appliedCoupon.code;

  const redeemCheckbox = document.getElementById("redeem-points");
  if (redeemCheckbox && redeemCheckbox.checked) payload.redeem_loyalty_points = true;

  const dineInTable = getDineInTable();
  if (fulfillmentType === "dine_in") {
    if (!dineInTable) {
      showToast("Table information was lost — please rescan the QR code on your table", "error");
      return;
    }
    payload.table_id = dineInTable.id;
  } else if (!getToken()) {
    payload.guest_name = document.getElementById("guest-name").value.trim();
    payload.guest_phone = document.getElementById("guest-phone").value.trim();
    payload.guest_email = document.getElementById("guest-email").value.trim() || null;
    if (!payload.guest_name || !payload.guest_phone) {
      showToast("Please enter your name and phone number", "error");
      return;
    }
  }

  if (fulfillmentType === "delivery") {
    payload.delivery_address = document.getElementById("delivery-address").value.trim();
    if (!payload.delivery_address) {
      showToast("Please enter a delivery address", "error");
      return;
    }
  }

  try {
    const result = await apiFetch("/checkout", { method: "POST", body: JSON.stringify(payload) });
    clearCart();
    clearDineInTable();
    window.location.href = result.checkout_url;
  } catch (err) {
    showToast(err.message, "error");
  }
}

init();
