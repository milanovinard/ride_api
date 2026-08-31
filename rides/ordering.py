"""
Custom ordering for the Ride List API.

A plain DRF `OrderingFilter` can't express "distance" as an orderable
field - it isn't a model field, it depends on query params (latitude/
longitude) supplied per-request. This backend handles both supported
orderings explicitly instead of forcing the distance case through
machinery built for static field names.
"""

from rest_framework.exceptions import ValidationError
from rest_framework.filters import BaseFilterBackend

from .distance import DISTANCE_ANNOTATION, annotate_distance

ORDERING_PARAM = "ordering"
LATITUDE_PARAM = "latitude"
LONGITUDE_PARAM = "longitude"

PICKUP_TIME_FIELD = "pickup_time"
DISTANCE_FIELD = "distance"
ORDERABLE_FIELDS = {PICKUP_TIME_FIELD, DISTANCE_FIELD}


class RideOrderingFilter(BaseFilterBackend):
    def filter_queryset(self, request, queryset, view):
        ordering = request.query_params.get(ORDERING_PARAM)
        if not ordering:
            return queryset

        descending = ordering.startswith("-")
        field = ordering[1:] if descending else ordering

        if field not in ORDERABLE_FIELDS:
            raise ValidationError(
                {
                    ORDERING_PARAM: (
                        f"Must be one of {sorted(ORDERABLE_FIELDS)}, "
                        "optionally prefixed with '-' for descending order."
                    )
                }
            )

        if field == PICKUP_TIME_FIELD:
            return queryset.order_by(f"-{PICKUP_TIME_FIELD}" if descending else PICKUP_TIME_FIELD)

        latitude, longitude = self._parse_coordinates(request)
        queryset = annotate_distance(queryset, latitude, longitude)
        return queryset.order_by(f"-{DISTANCE_ANNOTATION}" if descending else DISTANCE_ANNOTATION)

    @staticmethod
    def _parse_coordinates(request):
        raw_latitude = request.query_params.get(LATITUDE_PARAM)
        raw_longitude = request.query_params.get(LONGITUDE_PARAM)

        if raw_latitude is None or raw_longitude is None:
            raise ValidationError(
                {
                    ORDERING_PARAM: (
                        "Sorting by distance requires 'latitude' and 'longitude' "
                        "query parameters."
                    )
                }
            )

        try:
            return float(raw_latitude), float(raw_longitude)
        except ValueError:
            raise ValidationError(
                {
                    LATITUDE_PARAM: "Must be a valid number.",
                    LONGITUDE_PARAM: "Must be a valid number.",
                }
            )
