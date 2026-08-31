# Ride API

A Django REST Framework API for managing rides, riders, drivers, and ride
events.

## Stack

- Django 6.1 + Django REST Framework
- PostgreSQL
- JWT authentication (`djangorestframework-simplejwt`)
- `django-filter` for query-param filtering

## Setup

### Docker (recommended)

```bash
cp .env.example .env   # adjust SECRET_KEY etc. if you like
docker compose up --build
```

This starts Postgres and the Django dev server (`http://localhost:8000`).
Run migrations and create an admin user in a second terminal:

```bash
docker compose exec web python manage.py migrate
docker compose exec web python manage.py createsuperuser
```

The `createsuperuser` prompt creates a user with Django's `is_staff`/
`is_superuser` flags, but **API access is gated on the domain `role`
field, not those flags** (see [Authentication](#authentication)). After
creating the user, give it the admin role:

```bash
docker compose exec web python manage.py shell -c "
from accounts.models import User
u = User.objects.get(username='<the username you just created>')
u.role = User.Role.ADMIN
u.save()
"
```

### Local (without Docker)

Requires a local PostgreSQL instance matching the credentials in `.env`.

```bash
python -m venv venv
source venv/bin/activate   # venv\Scripts\activate on Windows
pip install -r requirements-dev.txt
cp .env.example .env
python manage.py migrate
python manage.py createsuperuser
python manage.py runserver
```

## Authentication

Authentication and authorization are two separate gates:

- **Login** (`POST /api/auth/login/`) checks credentials only. **Any** active
  user - admin, rider or driver - can log in and receive an `access` / `refresh`
  token pair.
- **Every business endpoint** requires a valid JWT **and** a user whose `role` is
  `admin` (`accounts.permissions.IsAdminRole`). A non-admin holds a perfectly
  valid token but still gets `403` from `/api/rides/`, `/api/users/`, etc. This is
  a domain rule, not Django's staff/superuser concept - a `role="rider"` user with
  `is_superuser=True` is still refused.

The access token carries only the user id; `role` is re-read from the database on
every request, so demoting an admin invalidates their existing token immediately.

| Endpoint | Auth | Purpose |
|----------|------|---------|
| `POST /api/auth/login/` | none | `{username, password}` -> `{user, access, refresh}` |
| `POST /api/auth/refresh/` | none | `{refresh}` -> `{access}` |
| `GET /api/auth/me/` | any logged-in user | the caller's own profile |

```bash
# Log in (any valid user)
curl -X POST http://localhost:8000/api/auth/login/ \
  -H "Content-Type: application/json" \
  -d '{"username": "<username>", "password": "<password>"}'
# -> {"user": {...}, "access": "<access>", "refresh": "<refresh>"}

# Call the API (must be an admin-role token, otherwise 403)
curl http://localhost:8000/api/rides/ -H "Authorization: Bearer <access>"

# Refresh when the access token expires
curl -X POST http://localhost:8000/api/auth/refresh/ \
  -H "Content-Type: application/json" \
  -d '{"refresh": "<refresh>"}'
```

## Endpoints

Standard CRUD ViewSets, all admin-only, all paginated
(`?page=`, `?page_size=`, default page size 20):

| Resource   | Path                | Notes |
|------------|---------------------|-------|
| Users      | `/api/users/`       | `password` is write-only and hashed on save. |
| Rides      | `/api/rides/`       | See [Ride List API](#ride-list-api) for `list`/`retrieve`. |
| Ride Events| `/api/ride-events/` | Plain CRUD. |

Every serializer field name matches the assessment's table definitions
(`id_ride`, `id_rider`, `id_driver`, `id_ride_event`, `id_user`) even
where the underlying Python attribute is named differently - see the
"Design notes" comments in `accounts/models.py` and `rides/models.py`.

### Ride List API

`GET /api/rides/` (and `retrieve`) returns each ride with:

- `id_rider` / `id_driver` - flat FK ids, per the spec's table definitions.
- `rider` / `driver` - nested `{id_user, first_name, last_name, email, role}`,
  fetched via `select_related` (zero extra queries).
- `todays_ride_events` - only the `RideEvent`s from the last 24 hours,
  fetched via a filtered `Prefetch` (one extra query for the whole page,
  never the full `RideEvent` table - see `rides/views.py`).

**Filtering**

- `?status=<status>` - exact match on Ride status.
- `?rider_email=<email>` - case-insensitive exact match on the rider's email.

**Sorting** - `?ordering=pickup_time|-pickup_time|distance|-distance`

Distance sort requires `?latitude=<float>&longitude=<float>` (the point
to measure distance from) and adds a `distance_km` field. Distance is
computed as an annotated SQL expression (haversine formula, see
`rides/distance.py`) so the database sorts and paginates without Python
ever holding the full Ride table in memory. A missing lat/lon, or an
unrecognized `ordering` value, returns `400` with a field-level error.

```bash
curl "http://localhost:8000/api/rides/?status=en-route&rider_email=alice@example.com&ordering=-pickup_time" \
  -H "Authorization: Bearer <access>"

curl "http://localhost:8000/api/rides/?ordering=distance&latitude=40.71&longitude=-74.00" \
  -H "Authorization: Bearer <access>"
```

## Query budget

The Ride List API is verified to issue exactly the queries the spec asks
for: 1 for the page of rides (with rider/driver folded in via SQL joins),
1 for the last-24-hours `RideEvent`s of that page, and 1 `COUNT` for
pagination - 3 total (a 4th, unavoidable query looks up the authenticated
user from the JWT, which is authentication overhead common to every
endpoint, not specific to this one).

## Design notes / trade-offs

- **Distance sort without a schema change.** The spec fixes the Ride
  table's columns (plain `pickup_latitude`/`pickup_longitude` floats, no
  PostGIS geometry column), so there's no spatial index available. The
  distance is computed as a per-row SQL expression (haversine, via
  `django.db.models.functions`) and the database sorts on it directly -
  the best available option under that constraint. A production system
  free to change the schema would store pickup location as a
  `geography(Point)` column with a GiST index, letting Postgres do a
  true index-driven nearest-neighbour search instead of evaluating trig
  functions per row.
- **Custom exceptions** (`common/exceptions.py`, `rides/exceptions.py`,
  `accounts/exceptions.py`) provide a small hierarchy of domain error
  types (`ResourceNotFoundError`, `ConflictError`, `PermissionDeniedError`
  and their subclasses) for any future business logic beyond plain CRUD
  (e.g. ride status transitions) to raise consistently. They're DRF
  `APIException` subclasses, so raising one is enough to get the right
  HTTP status and JSON body with no extra view code.
- **Why `role` and not `is_staff`/`is_superuser`.** The spec's access
  rule is about the domain `role` field ('admin' vs other roles), which
  is independent of Django's own auth concepts. Reusing `is_staff` would
  conflate "can log into the Django admin site" with "is an admin user
  of this API."

## Bonus - SQL report

Raw SQL (PostgreSQL) for: count of trips whose pickup-to-dropoff duration
exceeded 1 hour, grouped by month and driver.

Each ride's pickup/dropoff timestamps are computed first (grouped by
ride, taking the earliest matching event of each kind, in case of
duplicates), then filtered by duration, then counted per month/driver -
this avoids double-counting a ride if its `RideEvent`s were ever
duplicated.

```sql
WITH ride_durations AS (
    SELECT
        r.id_ride,
        r.id_driver,
        MIN(pickup.created_at)  AS pickup_at,
        MIN(dropoff.created_at) AS dropoff_at
    FROM ride r
    JOIN ride_event pickup
        ON pickup.id_ride = r.id_ride
       AND pickup.description = 'Status changed to pickup'
    JOIN ride_event dropoff
        ON dropoff.id_ride = r.id_ride
       AND dropoff.description = 'Status changed to dropoff'
    GROUP BY r.id_ride, r.id_driver
)
SELECT
    TO_CHAR(rd.pickup_at, 'YYYY-MM')                  AS month,
    TRIM(u.first_name || ' ' || LEFT(u.last_name, 1))  AS driver,
    COUNT(*)                                           AS count_of_trips_over_1hr
FROM ride_durations rd
JOIN "user" u ON u.id_user = rd.id_driver
WHERE rd.dropoff_at - rd.pickup_at > INTERVAL '1 hour'
GROUP BY month, driver
ORDER BY month, driver;
```

## Tests

```bash
pytest
```
