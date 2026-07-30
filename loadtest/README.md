# Load testing DokanPro

Uses [Locust](https://locust.io/) to simulate cashiers logging in once per
shift and repeatedly checking out, matching real POS usage patterns.

## Setup (one-time)

```bash
cd loadtest
python3 -m venv venv
source venv/bin/activate
pip install locust
```

## Before running against a target

Make sure `PRODUCT_ID` in `locustfile.py` has enough stock in every store
listed in `STORE_IDS` to survive the whole run — otherwise you'll see
false "out of stock" failures that aren't a performance problem:

```sql
UPDATE inventory SET quantity = 100000 WHERE product_id = 1;
```

Revert that afterwards if it's a real database, not disposable test data.

## Running

```bash
source venv/bin/activate
locust -f locustfile.py --host http://<your-server>:8000 \
  --users 35 --spawn-rate 10 --run-time 60s --headless
```

- `--users`: number of simulated cashiers/terminals active at once.
  Roughly `target_checkouts_per_second × avg_wait_time` (here, wait_time
  is 3-8s, so ~5.5s average) — e.g. for 6 checkouts/sec, ~35 users.
- `--spawn-rate`: how fast those users ramp up. A high spawn rate (e.g.
  ramping all users up within a few seconds) simulates a worst-case burst
  like every cashier logging in at store-opening time — a genuinely
  useful scenario to test, not just an artifact.
- Drop `--headless --run-time ...` and instead just run `locust -f
  locustfile.py --host ...` to get the web UI at http://localhost:8089
  for interactive, adjustable runs.

## What to look at in the results

- **`/api/orders` latency** (median + p95/p99) — this is what customers
  waiting at the register actually feel.
- **`/api/auth/login` latency** — a real bottleneck we found: bcrypt
  hashing is CPU-heavy, so a burst of simultaneous logins (e.g. many
  stores opening at once) can spike badly on a CPU-constrained box. This
  scales with available CPU cores and with `uvicorn --workers N` — it's
  not something you can fix with RAM alone.
- **Failure count/reasons** — check they're real errors (500s, timeouts),
  not business-logic 400s like insufficient stock or a missing
  `tendered` amount for cash payments.

## Cleaning up after a run against a real/shared database

Test orders land in `orders`/`order_items`/`stock_movements` like any
other sale. If you ran this against anything other than a fully
disposable test database, delete the orders it created (filter by
`created_at` around your test window) and restore any inventory
quantities you bumped for the test.
