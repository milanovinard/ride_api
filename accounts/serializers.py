"""
Serializers for the User model.

Field naming mirrors the spec's table definitions (`id_user`) even though
the Python/ORM-side attribute is Django's conventional `id` - see the
design notes in models.py. `UserSummarySerializer` is the compact,
read-only shape embedded in RideListSerializer (rides/serializers.py) so
the Ride List API can show rider/driver details with zero extra queries;
`UserSerializer` is the full read/write shape used by UserViewSet.
"""

from rest_framework import serializers

from .models import User


class UserSummarySerializer(serializers.ModelSerializer):
    id_user = serializers.IntegerField(source="id", read_only=True)

    class Meta:
        model = User
        fields = ["id_user", "first_name", "last_name", "email", "role"]
        read_only_fields = fields


class UserSerializer(serializers.ModelSerializer):
    id_user = serializers.IntegerField(source="id", read_only=True)
    password = serializers.CharField(
        write_only=True,
        required=False,
        style={"input_type": "password"},
    )

    class Meta:
        model = User
        fields = [
            "id_user",
            "username",
            "role",
            "first_name",
            "last_name",
            "email",
            "phone_number",
            "password",
        ]

    def create(self, validated_data):
        password = validated_data.pop("password", None)
        user = User(**validated_data)
        if password:
            user.set_password(password)
        else:
            user.set_unusable_password()
        user.save()
        return user

    def update(self, instance, validated_data):
        password = validated_data.pop("password", None)
        for field, value in validated_data.items():
            setattr(instance, field, value)
        if password:
            instance.set_password(password)
        instance.save()
        return instance
