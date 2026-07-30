import random
from locust import HttpUser, task, between

# Swap these for real store/product IDs from your production seed data.
STORE_IDS = [1, 2, 3]
PRODUCT_ID = 1

# Before running against real data: make sure PRODUCT_ID has enough stock
# in each store to survive the whole run, e.g.:
#   UPDATE inventory SET quantity = 100000 WHERE product_id = 1;
# (revert afterwards if this is real inventory, not a disposable test DB)


class Cashier(HttpUser):
    # Think-time between checkouts for one terminal: 3-8s, roughly matching
    # a real cashier scanning items and taking payment.
    wait_time = between(3, 8)

    def on_start(self):
        # Log in once per simulated terminal/cashier shift, not once per request.
        resp = self.client.post(
            "/api/auth/login",
            data={"username": "cashier@possystem.dev", "password": "cashier123"},
        )
        resp.raise_for_status()
        token = resp.json()["access_token"]
        self.client.headers.update({"Authorization": f"Bearer {token}"})
        self.store_id = random.choice(STORE_IDS)

    @task
    def checkout(self):
        payload = {
            "store_id": self.store_id,
            "items": [{"product_id": PRODUCT_ID, "qty": random.randint(1, 3)}],
            "payment_method": random.choice(["cash", "card", "bkash"]),
            "tendered": 1000,  # comfortably covers any possible cart total in this test
        }
        with self.client.post("/api/orders", json=payload, catch_response=True) as resp:
            if resp.status_code != 201:
                resp.failure(f"checkout failed: {resp.status_code} {resp.text[:200]}")
