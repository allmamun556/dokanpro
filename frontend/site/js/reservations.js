async function init() {
  await renderSiteNav("reservations.html");
  renderSiteFooter();

  if (getToken()) {
    document.getElementById("guest-fields").style.display = "none";
  }

  document.getElementById("reservation-form").addEventListener("submit", submitReservation);
}

async function submitReservation(e) {
  e.preventDefault();

  const payload = {
    party_size: parseInt(document.getElementById("r-party").value, 10),
    reservation_time: document.getElementById("r-time").value,
    notes: document.getElementById("r-notes").value.trim() || null,
  };

  if (!getToken()) {
    payload.guest_name = document.getElementById("r-name").value.trim();
    payload.guest_phone = document.getElementById("r-phone").value.trim();
    payload.guest_email = document.getElementById("r-email").value.trim() || null;
    if (!payload.guest_name || !payload.guest_phone) {
      showToast("Please enter your name and phone number", "error");
      return;
    }
  }

  try {
    const reservation = await apiFetch("/reservations", { method: "POST", body: JSON.stringify(payload) });
    document.getElementById("reservation-form").style.display = "none";
    const conf = document.getElementById("confirmation");
    conf.style.display = "block";
    conf.innerHTML = `
      <h3>Reservation Requested</h3>
      <p>We've received your request for <strong>${reservation.party_size} guests</strong> on
      <strong>${formatDate(reservation.reservation_time)}</strong>.</p>
      <p>We'll confirm shortly by phone or email. Reservation reference: #${reservation.id}</p>
    `;
  } catch (err) {
    showToast(err.message, "error");
  }
}

init();
