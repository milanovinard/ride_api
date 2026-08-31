"""
ViewSets for Ride and RideEvent.

RideViewSet.get_queryset applies the join/prefetch optimization described
in the spec (see rides/models.py's design notes) only for read actions:
- select_related("rider", "driver") folds the rider/driver lookups into
  the single SELECT for Ride as SQL joins - zero extra queries.
- Prefetch(..., to_attr="todays_ride_events") issues one extra query for
  *only* the last 24 hours of RideEvents (never the full table), scoped
  to the rides already on the current page.
That's 2 queries for the page's data, plus 1 COUNT query from pagination.
"""

from datetime import timedelta

from django.db.models import Prefetch
from django.utils import timezone
from django_filters.rest_framework import DjangoFilterBackend
from rest_framework import viewsets

from .filters import RideFilter
from .models import Ride, RideEvent
from .ordering import RideOrderingFilter
from .serializers import RideEventSerializer, RideListSerializer, RideSerializer

READ_ACTIONS = ("list", "retrieve")
TODAYS_EVENTS_WINDOW = timedelta(hours=24)


class RideViewSet(viewsets.ModelViewSet):
    queryset = Ride.objects.all()
    filter_backends = [DjangoFilterBackend, RideOrderingFilter]
    filterset_class = RideFilter

    def get_serializer_class(self):
        if self.action in READ_ACTIONS:
            return RideListSerializer
        return RideSerializer

    def get_queryset(self):
        queryset = super().get_queryset()
        if self.action not in READ_ACTIONS:
            return queryset

        cutoff = timezone.now() - TODAYS_EVENTS_WINDOW
        return queryset.select_related("rider", "driver").prefetch_related(
            Prefetch(
                "events",
                queryset=RideEvent.objects.filter(created_at__gte=cutoff),
                to_attr="todays_ride_events",
            )
        ).order_by("pickup_time")


class RideEventViewSet(viewsets.ModelViewSet):
    queryset = RideEvent.objects.select_related("ride").order_by("-created_at")
    serializer_class = RideEventSerializer
