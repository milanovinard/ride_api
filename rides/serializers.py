"""
Serializers for Ride and RideEvent.

Field naming mirrors the spec's table definitions (`id_ride`, `id_rider`,
`id_driver`, `id_ride_event`) even where the ORM-side attribute differs -
see the design notes in models.py for why each FK is named the Pythonic
way (`rider`, `ride`, ...) but column-mapped to the spec's names.

RideListSerializer extends RideSerializer (rather than duplicating its
fields) to add the read-only detail the Ride List API needs: nested
rider/driver summaries, `todays_ride_events`, and `distance_km`. It's only
used for list/retrieve (see RideViewSet.get_serializer_class) - writes go
through the plain RideSerializer, which takes rider/driver as plain FK ids.
"""

from rest_framework import serializers

from accounts.models import User
from accounts.serializers import UserSummarySerializer

from .models import Ride, RideEvent


class RideEventSerializer(serializers.ModelSerializer):
    id_ride = serializers.PrimaryKeyRelatedField(source="ride", queryset=Ride.objects.all())

    class Meta:
        model = RideEvent
        fields = ["id_ride_event", "id_ride", "description", "created_at"]


class RideSerializer(serializers.ModelSerializer):
    id_rider = serializers.PrimaryKeyRelatedField(source="rider", queryset=User.objects.all())
    id_driver = serializers.PrimaryKeyRelatedField(
        source="driver", queryset=User.objects.all(), allow_null=True, required=False
    )

    class Meta:
        model = Ride
        fields = [
            "id_ride",
            "status",
            "id_rider",
            "id_driver",
            "pickup_latitude",
            "pickup_longitude",
            "dropoff_latitude",
            "dropoff_longitude",
            "pickup_time",
        ]


class RideListSerializer(RideSerializer):
    rider = UserSummarySerializer(read_only=True)
    driver = UserSummarySerializer(read_only=True)
    todays_ride_events = RideEventSerializer(many=True, read_only=True)

    # Only present when ?ordering=distance is applied: RideOrderingFilter
    # annotates the queryset with `distance_km` (see rides/ordering.py and
    # rides/distance.py). Marked not-required so that when the annotation is
    # absent - every other request - DRF silently skips the field instead of
    # raising, keeping it out of the payload unless a distance sort produced it.
    distance_km = serializers.FloatField(read_only=True, required=False)

    class Meta(RideSerializer.Meta):
        fields = RideSerializer.Meta.fields + [
            "rider",
            "driver",
            "todays_ride_events",
            "distance_km",
        ]
