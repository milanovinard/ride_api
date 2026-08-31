from datetime import timedelta

from django.utils import timezone

from rides.models import Ride


def _make_ride(rider, driver, **overrides):
    defaults = dict(
        status=Ride.Status.EN_ROUTE,
        rider=rider,
        driver=driver,
        pickup_latitude=0.0,
        pickup_longitude=0.0,
        dropoff_latitude=0.0,
        dropoff_longitude=0.0,
        pickup_time=timezone.now(),
    )
    defaults.update(overrides)
    return Ride.objects.create(**defaults)


def test_filter_by_status(admin_client, rider_user, driver_user):
    _make_ride(rider_user, driver_user, status=Ride.Status.EN_ROUTE)
    _make_ride(rider_user, driver_user, status=Ride.Status.DROPOFF)

    response = admin_client.get("/api/rides/", {"status": "dropoff"})

    assert response.status_code == 200
    assert [r["status"] for r in response.data["results"]] == ["dropoff"]


def test_filter_by_rider_email(admin_client, rider_user, driver_user):
    _make_ride(rider_user, driver_user)

    matching = admin_client.get("/api/rides/", {"rider_email": rider_user.email})
    assert matching.data["count"] == 1

    no_match = admin_client.get("/api/rides/", {"rider_email": "nobody@example.com"})
    assert no_match.data["count"] == 0


def test_ordering_by_pickup_time(admin_client, rider_user, driver_user):
    now = timezone.now()
    earlier = _make_ride(rider_user, driver_user, pickup_time=now - timedelta(hours=1))
    later = _make_ride(rider_user, driver_user, pickup_time=now)

    response = admin_client.get("/api/rides/", {"ordering": "-pickup_time"})

    ids = [r["id_ride"] for r in response.data["results"]]
    assert ids == [later.id_ride, earlier.id_ride]


def test_ordering_by_distance_orders_nearest_first(admin_client, rider_user, driver_user):
    near = _make_ride(rider_user, driver_user, pickup_latitude=40.71, pickup_longitude=-74.00)
    far = _make_ride(rider_user, driver_user, pickup_latitude=34.05, pickup_longitude=-118.24)

    response = admin_client.get(
        "/api/rides/", {"ordering": "distance", "latitude": "40.7128", "longitude": "-74.0060"}
    )

    results = response.data["results"]
    assert [r["id_ride"] for r in results] == [near.id_ride, far.id_ride]

    # The distance sort must also surface the value it sorted on, ascending.
    distances = [r["distance_km"] for r in results]
    assert distances == sorted(distances)
    assert distances[0] < distances[1]


def test_distance_km_absent_when_not_sorting_by_distance(admin_client, rider_user, driver_user):
    _make_ride(rider_user, driver_user)

    [result] = admin_client.get("/api/rides/").data["results"]

    assert "distance_km" not in result


def test_ordering_by_distance_without_coordinates_is_rejected(admin_client):
    response = admin_client.get("/api/rides/", {"ordering": "distance"})
    assert response.status_code == 400


def test_unknown_ordering_field_is_rejected(admin_client):
    response = admin_client.get("/api/rides/", {"ordering": "not_a_field"})
    assert response.status_code == 400
