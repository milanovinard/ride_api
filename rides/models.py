"""
Ride and RideEvent models for the Ride API.

Design decisions (tied directly to the assessment's stated constraints):

1. FK fields are named the Pythonic way (`rider`, `driver`, `ride`) but
   pinned to the spec's literal column names via `db_column`
   (id_rider / id_driver / id_ride). That keeps `ride.rider`,
   `ride.rider_id` etc. idiomatic in code while the underlying SQL schema
   matches the table definitions in the guide exactly.

2. `on_delete` choices are deliberate:
   - Ride.rider / Ride.driver -> PROTECT. A Ride is a historical record;
     cascading a User deletion into deleting or nulling Rides would
     corrupt reporting data (e.g. the bonus SQL report grouped by driver).
   - RideEvent.ride -> CASCADE. RideEvents have no meaning without their
     parent Ride.

3. `driver` is nullable (a Ride can exist before a driver is assigned);
   `rider` is required.

4. Every field the Ride List API filters or sorts on is indexed:
   - `status`: indexed alone and combined with `pickup_time` in a
     composite index (the expected query shape is filter-then-sort).
   - `pickup_time`: indexed on its own too.
   - `pickup_latitude` / `pickup_longitude`: a composite B-tree index
     supports a bounding-box pre-filter before computing exact distance -
     not a true spatial index, but the best option given the constraint
     that the Ride table structure can't change (no new geo column).
   - Rider email filtering hits the `User.email` index via the FK join.

5. Django auto-indexes ForeignKey columns, so `rider_id`/`driver_id` are
   already indexed without extra declarations.

6. RideEvent gets a composite index on (ride, created_at) because every
   read pattern in the spec is "this ride's events in a time range": the
   last-24-hours slice for `todays_ride_events`, and pairing pickup/dropoff
   timestamps for the bonus duration report.

7. The two known RideEvent descriptions used for duration calculations
   are pulled out as constants so app code and the SQL/README stay in sync.
"""

from django.conf import settings
from django.db import models


class Ride(models.Model):
    class Status(models.TextChoices):
        REQUESTED = "requested", "Requested"
        EN_ROUTE = "en-route", "En route"
        PICKUP = "pickup", "Pickup"
        DROPOFF = "dropoff", "Dropoff"
        CANCELLED = "cancelled", "Cancelled"

    id_ride = models.AutoField(primary_key=True)

    status = models.CharField(
        max_length=20,
        choices=Status.choices,
        db_index=True,
    )

    rider = models.ForeignKey(
        settings.AUTH_USER_MODEL,
        db_column="id_rider",
        related_name="rides_as_rider",
        on_delete=models.PROTECT,
    )
    driver = models.ForeignKey(
        settings.AUTH_USER_MODEL,
        db_column="id_driver",
        related_name="rides_as_driver",
        on_delete=models.PROTECT,
        null=True,
        blank=True,
    )

    pickup_latitude = models.FloatField()
    pickup_longitude = models.FloatField()
    dropoff_latitude = models.FloatField()
    dropoff_longitude = models.FloatField()

    pickup_time = models.DateTimeField(db_index=True)

    class Meta:
        db_table = "ride"
        indexes = [
            models.Index(fields=["status", "pickup_time"], name="ride_status_pickup_idx"),
            models.Index(
                fields=["pickup_latitude", "pickup_longitude"],
                name="ride_pickup_geo_idx",
            ),
        ]

    def __str__(self):
        return f"Ride #{self.id_ride} ({self.status})"


class RideEvent(models.Model):
    STATUS_CHANGED_TO_PICKUP = "Status changed to pickup"
    STATUS_CHANGED_TO_DROPOFF = "Status changed to dropoff"

    id_ride_event = models.AutoField(primary_key=True)

    ride = models.ForeignKey(
        Ride,
        db_column="id_ride",
        related_name="events",
        on_delete=models.CASCADE,
    )

    description = models.CharField(max_length=255)
    created_at = models.DateTimeField(db_index=True)

    class Meta:
        db_table = "ride_event"
        ordering = ["created_at"]
        indexes = [
            models.Index(fields=["ride", "created_at"], name="ride_event_ride_created_idx"),
        ]

    def __str__(self):
        return f"RideEvent #{self.id_ride_event} for Ride #{self.ride_id}: {self.description}"
