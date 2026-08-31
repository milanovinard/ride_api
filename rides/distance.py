"""
Great-circle distance from a fixed point to each Ride's pickup location,
computed entirely in SQL so sorting/pagination never has to pull the full
Ride table into Python.

The Ride table can't gain a geography column (spec constraint), so this
isn't a real spatial index lookup - Postgres still evaluates the
trig expression per candidate row. It's the best available option given
that constraint; a production system storing pickup location as a
`geography(Point)` column with a GiST index would let the database do a
true index-driven nearest-neighbour search instead.

Uses the haversine (ASIN/SQRT) formula rather than the more common
ACOS form: ACOS's argument can drift fractionally outside [-1, 1] from
floating-point rounding when two points coincide or are antipodal,
raising a domain error in Postgres. ASIN/SQRT's argument is always
non-negative and effectively bounded at 1, so it doesn't need clamping.
"""

from django.db.models import ExpressionWrapper, F, FloatField, Value
from django.db.models.functions import ASin, Cos, Power, Radians, Sin, Sqrt
from django.db.models.query import QuerySet

EARTH_RADIUS_KM = 6371.0

DISTANCE_ANNOTATION = "distance_km"


def _radians(value):
    return Radians(ExpressionWrapper(value, output_field=FloatField()))


def annotate_distance(queryset: QuerySet, latitude: float, longitude: float) -> QuerySet:
    """Annotate each row with `distance_km`: the haversine distance in
    kilometres from (latitude, longitude) to the ride's pickup point."""

    origin_lat = _radians(Value(latitude, output_field=FloatField()))
    origin_lon = _radians(Value(longitude, output_field=FloatField()))
    pickup_lat = _radians(F("pickup_latitude"))
    pickup_lon = _radians(F("pickup_longitude"))

    half_dlat = (pickup_lat - origin_lat) / 2.0
    half_dlon = (pickup_lon - origin_lon) / 2.0

    haversine = Power(Sin(half_dlat), 2.0) + Cos(origin_lat) * Cos(pickup_lat) * Power(
        Sin(half_dlon), 2.0
    )

    distance_km = 2 * EARTH_RADIUS_KM * ASin(Sqrt(haversine))

    return queryset.annotate(
        **{DISTANCE_ANNOTATION: ExpressionWrapper(distance_km, output_field=FloatField())}
    )
