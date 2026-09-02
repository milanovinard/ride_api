"""
Seed a deterministic dataset for the bonus SQL report and verify the query
produces the expected result.

    python manage.py seed_bonus_data          # seed, then run + check the report
    python manage.py seed_bonus_data --sql    # skip seeding; just run the report
    python manage.py seed_bonus_data --reset  # remove this command's data and exit

Docker:

    docker compose exec web python manage.py seed_bonus_data

The dataset is built so every branch of the bonus query is exercised:

- trips well over an hour (counted)
- a 30-minute trip (excluded)
- an exactly-60-minute trip (excluded - the query uses `> INTERVAL '1 hour'`)
- a trip with a DUPLICATE 'Status changed to pickup' event (must still count once,
  because the CTE takes MIN(created_at) and groups by ride)
- a trip with a pickup but NO dropoff event (excluded by the INNER JOIN)

Re-running is safe: it deletes any rides previously seeded for these drivers
(their events cascade) and recreates them.
"""

from datetime import datetime, timedelta

from django.core.management.base import BaseCommand
from django.db import connection, transaction

from accounts.models import User
from rides.models import Ride, RideEvent

# Kept in sync with README, section "Bonus - SQL".
REPORT_SQL = """
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
    TO_CHAR(rd.pickup_at, 'YYYY-MM')                   AS month,
    TRIM(u.first_name || ' ' || LEFT(u.last_name, 1))  AS driver,
    COUNT(*)                                           AS count_of_trips_over_1hr
FROM ride_durations rd
JOIN "user" u ON u.id_user = rd.id_driver
WHERE rd.dropoff_at - rd.pickup_at > INTERVAL '1 hour'
GROUP BY month, driver
ORDER BY month, driver;
"""

RIDER = dict(
    username="bonus_rider", first_name="Rita", last_name="Ortiz",
    email="bonus_rider@example.com", role=User.Role.RIDER,
)

DRIVERS = {
    "chris": dict(username="bonus_chris", first_name="Chris", last_name="Hunt",
                  email="bonus_chris@example.com", role=User.Role.DRIVER),
    "howard": dict(username="bonus_howard", first_name="Howard", last_name="Young",
                   email="bonus_howard@example.com", role=User.Role.DRIVER),
    "randy": dict(username="bonus_randy", first_name="Randy", last_name="West",
                  email="bonus_randy@example.com", role=User.Role.DRIVER),
}

# (driver key, pickup timestamp, trip minutes | None for "no dropoff", note)
RIDES = [
    ("chris",  "2024-01-05T08:00:00+00:00", 90,   "counts"),
    ("chris",  "2024-01-12T14:00:00+00:00", 120,  "counts"),
    ("chris",  "2024-01-20T19:00:00+00:00", 30,   "under 1h -> excluded"),
    ("howard", "2024-01-03T07:30:00+00:00", 75,   "counts"),
    ("howard", "2024-01-15T09:00:00+00:00", 200,  "counts"),
    ("howard", "2024-01-27T22:00:00+00:00", 61,   "counts"),
    ("randy",  "2024-01-09T11:00:00+00:00", 130,  "counts"),
    ("chris",  "2024-02-07T06:00:00+00:00", 95,   "counts"),
    ("randy",  "2024-02-11T16:00:00+00:00", 70,   "counts"),
    ("randy",  "2024-02-25T18:30:00+00:00", 240,  "counts"),
    ("howard", "2024-03-04T05:00:00+00:00", 60,   "exactly 1h -> NOT > 1h, excluded"),
    ("howard", "2024-03-18T13:00:00+00:00", 61,   "counts"),
    ("randy",  "2024-04-02T10:00:00+00:00", 80,   "counts; also gets a duplicate pickup event"),
    ("chris",  "2024-04-06T10:00:00+00:00", None, "pickup only, no dropoff -> excluded"),
]

EXPECTED = [
    ("2024-01", "Chris H", 2),
    ("2024-01", "Howard Y", 3),
    ("2024-01", "Randy W", 1),
    ("2024-02", "Chris H", 1),
    ("2024-02", "Randy W", 2),
    ("2024-03", "Howard Y", 1),
    ("2024-04", "Randy W", 1),
]

GEO = dict(
    pickup_latitude=40.7128, pickup_longitude=-74.0060,
    dropoff_latitude=40.7306, dropoff_longitude=-73.9866,
)


class Command(BaseCommand):
    help = "Seed deterministic data for the bonus SQL report and verify the query."

    def add_arguments(self, parser):
        parser.add_argument(
            "--reset", action="store_true",
            help="Delete rides/events seeded by this command and exit.",
        )
        parser.add_argument(
            "--sql", action="store_true",
            help="Skip seeding; just run the report SQL against the current data.",
        )

    @transaction.atomic
    def handle(self, *args, **options):
        if options["sql"]:
            self._run_report()
            return

        drivers = {
            key: User.objects.get_or_create(username=cfg["username"], defaults=cfg)[0]
            for key, cfg in DRIVERS.items()
        }
        rider = User.objects.get_or_create(username=RIDER["username"], defaults=RIDER)[0]

        # Idempotent: clear anything this command seeded before (events cascade).
        deleted, _ = Ride.objects.filter(driver__in=drivers.values()).delete()
        if options["reset"]:
            self.stdout.write(self.style.WARNING(
                f"Removed {deleted} seeded ride/ride_event rows."
            ))
            return

        rides = events = 0
        for key, pickup_iso, minutes, note in RIDES:
            pickup_at = datetime.fromisoformat(pickup_iso)
            ride = Ride.objects.create(
                status=Ride.Status.DROPOFF, rider=rider, driver=drivers[key],
                pickup_time=pickup_at, **GEO,
            )
            rides += 1

            RideEvent.objects.create(
                ride=ride, description=RideEvent.STATUS_CHANGED_TO_PICKUP,
                created_at=pickup_at,
            )
            events += 1

            if "duplicate pickup" in note:
                RideEvent.objects.create(
                    ride=ride, description=RideEvent.STATUS_CHANGED_TO_PICKUP,
                    created_at=pickup_at + timedelta(minutes=15),
                )
                events += 1

            if minutes is not None:
                RideEvent.objects.create(
                    ride=ride, description=RideEvent.STATUS_CHANGED_TO_DROPOFF,
                    created_at=pickup_at + timedelta(minutes=minutes),
                )
                events += 1

        self.stdout.write(self.style.SUCCESS(
            f"Seeded {rides} rides and {events} ride events "
            f"(rider: {rider.get_full_name()}; drivers: "
            f"{', '.join(d.get_full_name() for d in drivers.values())})."
        ))
        self._run_report()

    def _run_report(self):
        with connection.cursor() as cursor:
            cursor.execute(REPORT_SQL)
            rows = [(m, d, int(c)) for m, d, c in cursor.fetchall()]

        self.stdout.write("")
        self.stdout.write("Bonus report - trips over 1 hour, by month and driver")
        self.stdout.write("-" * 52)
        self.stdout.write(f"{'month':<10}{'driver':<12}count_of_trips_over_1hr")
        for month, driver, count in rows:
            self.stdout.write(f"{month:<10}{driver:<12}{count}")

        if rows == EXPECTED:
            self.stdout.write(self.style.SUCCESS(
                "\nMatches the expected result - bonus SQL verified."
            ))
        else:
            self.stdout.write(self.style.ERROR("\nMISMATCH - expected:"))
            for row in EXPECTED:
                self.stdout.write(f"  {row[0]:<10}{row[1]:<12}{row[2]}")
