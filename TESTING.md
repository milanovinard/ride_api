# Testing Guide

Two ways to exercise this project:

- **Part 1 – Automated tests** (`pytest`): the 21 tests shipped in `accounts/tests/`
  and `rides/tests/`.
- **Part 2 – Manual / functional testing with Postman**: every endpoint, plus the
  filtering, sorting, pagination and auth-failure behaviour of the Ride List API.

---

## Part 1 – Automated tests (pytest)

### 1.1 What the suite covers

| File | Tests | What it verifies |
|------|-------|------------------|
| `accounts/tests/test_auth.py` | 7 | Any valid user can `POST /api/auth/login/` and gets `{user, access, refresh}`; wrong password → `401`; a non-admin token → `403` from `/api/rides/` while an admin token → `200`; `refresh` returns a new access token; `me` returns the caller and needs auth. |
| `accounts/tests/test_permissions.py` | 3 | Anonymous request → `401`; non-admin role → `403`; admin role → `200`. |
| `accounts/tests/test_users_api.py` | 1 | `POST /api/users/` hashes the password and never returns it. |
| `rides/tests/test_ride_list_api.py` | 3 | `todays_ride_events` excludes events older than 24 h; each ride carries both flat (`id_rider`/`id_driver`) and nested (`rider`/`driver`) data; the list endpoint runs in **≤ 3 queries** (`django_assert_max_num_queries(3)`). |
| `rides/tests/test_ride_filters_and_ordering.py` | 7 | Filter by `status`; filter by `rider_email`; sort by `pickup_time`; sort by `distance` (nearest first); `distance_km` is returned and ascending when sorting by distance; `distance_km` is absent otherwise; `ordering=distance` without coordinates → `400`; unknown `ordering` value → `400`. |

The fixtures live in `conftest.py` (`admin_user`, `rider_user`, `driver_user`,
`admin_client`, `rider_client`). `pytest.ini` sets `DJANGO_SETTINGS_MODULE=config.settings`.

> The project uses **`pytest` only** – do not use `python manage.py test` (the tests
> are pytest-style functions with fixtures, not `django.test.TestCase` classes).

> A PostgreSQL database is **required** – `config/settings.py` pins the
> `django.db.backends.postgresql` engine, and `pytest-django` creates a throwaway
> `test_<db name>` database when the run starts.

---

### 1.2 Option A – Run tests in Docker (recommended)

Nothing to install except Docker Desktop. This matches the environment described in
`README.md`.

**Step 1 – Create your env file** (once):

```bash
cp .env.example .env
```

**Step 2 – Start the stack** (Postgres + Django):

```bash
docker compose up --build -d
```

**Step 3 – Run the whole suite:**

```bash
docker compose exec web pytest
```

Expected tail of the output:

```
============================= 21 passed in 3.80s ==============================
```

**One-off alternative** (starts `db` via `depends_on`, runs, then removes the
container – no need for `up` first):

```bash
docker compose run --rm web pytest
```

**Stop everything when done:**

```bash
docker compose down
```

---

### 1.3 Option B – Run tests locally (virtualenv + local Postgres)

**Step 1 – Create and activate a virtualenv:**

```bash
python -m venv venv
```

```bash
# Windows PowerShell
venv\Scripts\Activate.ps1
# macOS / Linux
source venv/bin/activate
```

**Step 2 – Install dependencies (dev set includes pytest, coverage, ruff, black):**

```bash
pip install -r requirements-dev.txt
```

**Step 3 – Provide a local PostgreSQL database.**
Connect to your local Postgres as a superuser and run:

```sql
CREATE ROLE ride_api WITH LOGIN PASSWORD 'ride_api';
CREATE DATABASE ride_api OWNER ride_api;
ALTER ROLE ride_api CREATEDB;   -- lets pytest-django create the test_ride_api database
```

**Step 4 – Point the app at localhost.**
Copy the env file and change the host (in Docker it is `db`; locally it is
`localhost`):

```bash
cp .env.example .env
```

```ini
# .env
POSTGRES_HOST=localhost
```

**Step 5 – Run the suite:**

```bash
pytest
```

---

### 1.4 Useful test commands

```bash
pytest -v                                   # one line per test
pytest -x                                    # stop at the first failure
pytest -k query_budget                       # only tests whose name matches
pytest accounts/                             # only the accounts app
pytest rides/tests/test_ride_list_api.py     # a single file
pytest rides/tests/test_ride_list_api.py::test_ride_list_query_budget   # a single test
pytest --reuse-db                            # keep the test DB between runs (faster)
pytest --create-db --reuse-db                # rebuild the test DB once, then reuse
```

Prefix with `docker compose exec web ` when using Option A, e.g.
`docker compose exec web pytest -v`.

---

### 1.5 Coverage report (optional)

`coverage` is already in `requirements-dev.txt`.

```bash
coverage run -m pytest
coverage report -m
```

(Docker: `docker compose exec web coverage run -m pytest && docker compose exec web coverage report -m`.)

---

### 1.6 Code-style checks (optional)

```bash
ruff check .
black --check .
```

---

### 1.7 Troubleshooting

| Symptom | Cause / fix |
|---------|-------------|
| `could not translate host name "db"` | Running Option B with the Docker host. Set `POSTGRES_HOST=localhost` in `.env`. |
| `permission denied to create database` | The `ride_api` role lacks `CREATEDB`. Run `ALTER ROLE ride_api CREATEDB;`. |
| `connection refused` on port 5432 | Postgres is not running, or Docker `db` is still starting. `docker compose ps` / start your local Postgres. |
| `django.db.utils.OperationalError` about `test_ride_api` | Leftover test DB from an interrupted run. Re-run with `pytest --create-db`. |
| Tests can't find `config.settings` | Run `pytest` from the repo root (where `pytest.ini` lives). |

---

## Part 2 – Manual API testing with Postman

Every endpoint requires **(a)** a valid JWT and **(b)** a user whose `role` is
`admin`. The steps below build up data and then read it back through the Ride List
API.

An importable collection with assertions is provided at
[`docs/Ride_API.postman_collection.json`](docs/Ride_API.postman_collection.json) –
see [2.9](#29-run-the-entire-collection-at-once) to run it all at once.

### 2.1 Prerequisites

- The API running on `http://localhost:8000` (see below).
- Postman (desktop app or web).

**Start the API with Docker:**

```bash
docker compose up --build -d
docker compose exec web python manage.py migrate
```

(or, locally: `python manage.py migrate` then `python manage.py runserver`.)

### 2.2 Step 0 – Create the first admin user

The API is admin-only, so the first admin cannot be created through the API. Create
it from the shell:

```bash
docker compose exec web python manage.py shell -c "from accounts.models import User; User.objects.create_user(username='admin', password='admin12345', email='admin@example.com', role='admin')"
```

(Local, no Docker: drop `docker compose exec web `.)

### 2.3 Step 1 – Import the collection

1. Postman → **Import** → select `docs/Ride_API.postman_collection.json`.
2. Open the collection → **Variables** tab. Confirm/adjust:
   - `base_url` = `http://localhost:8000`
   - `admin_username` = `admin`
   - `admin_password` = `admin12345`
3. The collection's **Authorization** is preset to *Bearer Token* =
   `{{access_token}}`, so every request inherits the token once you have one.

### 2.4 Step 2 – Log in  (`POST /api/auth/login/`)

**Request** – folder *Auth → Login (admin)*:

- Method / URL: `POST {{base_url}}/api/auth/login/`
- Body (raw JSON):
  ```json
  { "username": "{{admin_username}}", "password": "{{admin_password}}" }
  ```

**Expected response** `200 OK`:

```json
{
  "user": { "id_user": 1, "username": "admin", "role": "admin", "first_name": "", "last_name": "", "email": "admin@example.com", "phone_number": "" },
  "access": "eyJhbGci...",
  "refresh": "eyJhbGci..."
}
```

Any active user can log in here – a rider or driver also gets `200` and a token
pair. What that token may *do* is enforced per-request (see 2.10). Bad
credentials → `401`.

The request's *Tests* script stores `access` → `access_token` and `refresh` →
`refresh_token` collection variables automatically. Every later request uses
`access_token`.

> Manual alternative: copy the `access` value and, on each request, set header
> `Authorization: Bearer <access>`.

### 2.5 Step 3 – Users  (`/api/users/`)

| # | Request | Method & URL | Body | Expect |
|---|---------|--------------|------|--------|
| 3a | Create rider | `POST {{base_url}}/api/users/` | `{"username":"rider_alice","role":"rider","first_name":"Alice","last_name":"Ng","email":"alice@example.com","phone_number":"+15551110001","password":"riderpass123"}` | `201`; body has `id_user`, **no** `password` |
| 3b | Create driver | `POST {{base_url}}/api/users/` | `{"username":"driver_bob","role":"driver","first_name":"Bob","last_name":"Lee","email":"bob@example.com","phone_number":"+15551110002","password":"driverpass123"}` | `201` |
| 3c | List users | `GET {{base_url}}/api/users/` | – | `200`; paginated (`count`, `next`, `previous`, `results`) |
| 3d | Retrieve user | `GET {{base_url}}/api/users/{{rider_id}}/` | – | `200`; the rider |
| 3e | Update user | `PATCH {{base_url}}/api/users/{{rider_id}}/` | `{"phone_number":"+15559990000"}` | `200`; `phone_number` changed |
| 3f | Delete user | `DELETE {{base_url}}/api/users/{{driver_id}}/` | – | `204` (run this **last**, or skip – the ride needs the driver) |

The collection's *Create rider* / *Create driver* scripts save `id_user` into
`rider_id` and `driver_id`.

### 2.6 Step 4 – Rides  (`/api/rides/`)

| # | Request | Method & URL | Body | Expect |
|---|---------|--------------|------|--------|
| 4a | Create ride | `POST {{base_url}}/api/rides/` | see below | `201`; body has `id_ride` |
| 4b | Retrieve ride | `GET {{base_url}}/api/rides/{{ride_id}}/` | – | `200`; includes `rider`, `driver`, `todays_ride_events` |
| 4c | Update status | `PATCH {{base_url}}/api/rides/{{ride_id}}/` | `{"status":"pickup"}` | `200` |
| 4d | Delete ride | `DELETE {{base_url}}/api/rides/{{ride_id}}/` | – | `204` (run last) |

**4a body:**

```json
{
  "status": "en-route",
  "id_rider": {{rider_id}},
  "id_driver": {{driver_id}},
  "pickup_latitude": 40.7128,
  "pickup_longitude": -74.0060,
  "dropoff_latitude": 40.7306,
  "dropoff_longitude": -73.9866,
  "pickup_time": "2026-09-01T09:00:00Z"
}
```

- `status` is required and must be one of: `requested`, `en-route`, `pickup`,
  `dropoff`, `cancelled`.
- `id_driver` is optional/nullable; `id_rider` is required.
- The *Create ride* script saves `id_ride` → `ride_id`.

### 2.7 Step 5 – Ride events  (`/api/ride-events/`)

Create one **recent** and one **old** event so you can see the 24-hour window work.

| # | Request | Method & URL | Body | Expect |
|---|---------|--------------|------|--------|
| 5a | Recent event | `POST {{base_url}}/api/ride-events/` | `{"id_ride":{{ride_id}},"description":"Status changed to pickup","created_at":"{{$isoTimestamp}}"}` | `201` |
| 5b | Old event | `POST {{base_url}}/api/ride-events/` | `{"id_ride":{{ride_id}},"description":"Status changed to dropoff","created_at":"2026-07-01T09:00:00Z"}` | `201` |
| 5c | List events | `GET {{base_url}}/api/ride-events/` | – | `200`; paginated |
| 5d | Retrieve event | `GET {{base_url}}/api/ride-events/{{ride_event_id}}/` | – | `200` |
| 5e | Update event | `PATCH {{base_url}}/api/ride-events/{{ride_event_id}}/` | `{"description":"Status changed to pickup (corrected)"}` | `200` |
| 5f | Delete event | `DELETE {{base_url}}/api/ride-events/{{ride_event_id}}/` | – | `204` |

- `created_at` has no server default – you must send it.
- `{{$isoTimestamp}}` is a Postman dynamic variable that resolves to "now" in UTC.

### 2.8 Step 6 – The Ride List API (filter / sort / paginate)

All against `GET {{base_url}}/api/rides/`.

| # | Query string | Expect |
|---|--------------|--------|
| 6a | *(none)* | `200`; `results[].todays_ride_events` contains **only** the recent event (not the 2026‑07‑01 one); each result has nested `rider`/`driver` |
| 6b | `?page=1&page_size=5` | `200`; at most 5 results; `count` reflects the total |
| 6c | `?status=en-route` | `200`; every result has `status` = `en-route` |
| 6d | `?rider_email=alice@example.com` | `200`; only Alice's rides (case-insensitive) |
| 6e | `?ordering=pickup_time` | `200`; results ascending by `pickup_time` |
| 6f | `?ordering=-pickup_time` | `200`; results descending by `pickup_time` |
| 6g | `?ordering=distance&latitude=40.7128&longitude=-74.0060` | `200`; results ascending by distance; each result now has a **`distance_km`** field |
| 6h | `?ordering=-distance&latitude=40.7128&longitude=-74.0060` | `200`; farthest first |
| 6i | `?ordering=distance` *(no lat/lon)* | `400`; error under the `ordering` key |
| 6j | `?ordering=not_a_field` | `400`; error listing the allowed values |

> Tip: create a second ride at a far pickup point (e.g.
> `pickup_latitude: 34.05, pickup_longitude: -118.24`) before running 6g/6h so the
> ordering is visible.

### 2.9 Step 7 – Check the caller  (`GET /api/auth/me/`)

- `GET {{base_url}}/api/auth/me/` (inherits the collection Bearer token)
- Expect `200` with the current user's profile. Works for any logged-in user
  (permission is `IsAuthenticated`, not admin-only). No token → `401`.

### 2.10 Step 8 – Refresh the token  (`POST /api/auth/refresh/`)

- `POST {{base_url}}/api/auth/refresh/`
- Body: `{ "refresh": "{{refresh_token}}" }`
- Expect `200` with a fresh `access`. The *Tests* script updates `access_token`.

### 2.11 Step 9 – Auth-failure cases

| # | Request | Expect |
|---|---------|--------|
| 9a | `GET {{base_url}}/api/rides/` with **no** `Authorization` header (request auth = *No Auth*) | `401` |
| 9b | Log in as the **rider** (`POST /api/auth/login/` with the rider's username / `riderpass123`), then `GET {{base_url}}/api/rides/` with that token | `403` – valid token, role is not `admin` |
| 9c | `GET {{base_url}}/api/rides/` with a malformed token (`Authorization: Bearer abc.def.ghi`) | `401` |

The collection's *Auth failure cases* folder wires 9a–9c up (9b logs in and stores
`rider_access_token` and overrides the request auth to use it).

### 2.12 Run the entire collection at once

1. Hover the **Ride API** collection → **⋯** → **Run collection**.
2. Order the requests: *Auth → Users → Rides → Ride Events → Ride List API →
   Auth failure cases* (this is the default order in the file).
3. **Run Ride API**.

Every request carries `pm.test(...)` assertions, so the runner shows a green/red
summary – a full functional pass of the API in one click. Re-running is safe: the
create steps make fresh records each time (unique `username`/`email` use a
`{{$timestamp}}` suffix in the collection).

### 2.13 Endpoint reference

| Resource | Endpoint | Methods | Notes |
|----------|----------|---------|-------|
| Login | `/api/auth/login/` | `POST` | No auth. `{username, password}` → `{user, access, refresh}`. Any active user. |
| Token refresh | `/api/auth/refresh/` | `POST` | No auth. `{refresh}` → `{access}` |
| Current user | `/api/auth/me/` | `GET` | Any authenticated user (not admin-only). Returns the caller's profile. |
| Users | `/api/users/` | `GET`, `POST` | `POST` body: `username`, `role`, `first_name`, `last_name`, `email`, `phone_number`, `password` (write-only) |
| User detail | `/api/users/{id}/` | `GET`, `PUT`, `PATCH`, `DELETE` | |
| Rides | `/api/rides/` | `GET`, `POST` | `GET` supports `page`, `page_size` (≤100), `status`, `rider_email`, `ordering` (`pickup_time`/`-pickup_time`/`distance`/`-distance`), `latitude`, `longitude` |
| Ride detail | `/api/rides/{id}/` | `GET`, `PUT`, `PATCH`, `DELETE` | `GET` includes nested `rider`, `driver`, `todays_ride_events` |
| Ride events | `/api/ride-events/` | `GET`, `POST` | `POST` body: `id_ride`, `description`, `created_at` |
| Ride event detail | `/api/ride-events/{id}/` | `GET`, `PUT`, `PATCH`, `DELETE` | |

`/api/auth/login/` and `/api/auth/refresh/` need no auth; `/api/auth/me/` needs any
valid token. **Every other endpoint** requires a JWT (`Authorization: Bearer
<access>`) **and** caller `role == "admin"`; otherwise `401` (no/invalid token) or
`403` (valid token, wrong role).
