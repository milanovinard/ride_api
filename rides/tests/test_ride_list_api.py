from datetime import timedelta

from django.utils import timezone

from rides.models import Ride, RideEvent


def _make_ride(rider, driver, **overrides):
    defaults = dict(
        status=Ride.Status.EN_ROUTE,
        rider=rider,
        driver=driver,
        pickup_latitude=40.7128,
        pickup_longitude=-74.0060,
        dropoff_latitude=40.73,
        dropoff_longitude=-73.99,
        pickup_time=timezone.now(),
    )
    defaults.update(overrides)
    return Ride.objects.create(**defaults)


def test_todays_ride_events_excludes_events_older_than_24h(admin_client, rider_user, driver_user):
    ride = _make_ride(rider_user, driver_user)
    now = timezone.now()

    recent = RideEvent.objects.create(ride=ride, description="recent", created_at=now - timedelta(hours=1))
    old = RideEvent.objects.create(ride=ride, description="old", created_at=now - timedelta(hours=48))

    response = admin_client.get("/api/rides/")

    assert response.status_code == 200
    [result] = response.data["results"]
    event_descriptions = {e["description"] for e in result["todays_ride_events"]}
    assert event_descriptions == {"recent"}
    assert old.description not in event_descriptions


def test_ride_list_includes_flat_and_nested_rider_driver(admin_client, rider_user, driver_user):
    ride = _make_ride(rider_user, driver_user)

    response = admin_client.get("/api/rides/")

    [result] = response.data["results"]
    assert result["id_ride"] == ride.id_ride
    assert result["id_rider"] == rider_user.id
    assert result["id_driver"] == driver_user.id
    assert result["rider"]["email"] == rider_user.email
    assert result["driver"]["email"] == driver_user.email


def test_ride_list_query_budget(admin_client, rider_user, driver_user, django_assert_max_num_queries):
    _make_ride(rider_user, driver_user)
    _make_ride(rider_user, driver_user)

    # 1 for the ride page (rider/driver joined in), 1 for the filtered
    # RideEvent prefetch, 1 COUNT for pagination.
    with django_assert_max_num_queries(3):
        response = admin_client.get("/api/rides/")
        assert response.status_code == 200
