"""
User model for the Ride API.

Design decisions:
- Extends Django's AbstractUser instead of a plain model so we get password
  hashing, auth backends, permissions, and admin integration for free -
  the alternative (a bare `User` model + a separate auth scheme) would mean
  re-implementing login/permission machinery the spec doesn't ask for.
- `id_user` is exposed as the literal primary-key column name via
  `db_column`, matching the spec's table definition, while the Python-side
  attribute stays Django's conventional `id` / `pk`.
- `role` drives the "admin-only" access requirement. It's a small closed
  set of choices rather than a free-text field or a separate
  Group/Permission setup - simplest thing that satisfies the requirement
  without over-engineering a permissions system the spec doesn't ask for.
- `email` is unique + indexed because the Ride List API must filter by
  rider email; without the index that filter becomes a sequential scan
  once the User table grows.
- AbstractUser already provides `first_name`/`last_name`; we don't
  redeclare them.
"""

from django.contrib.auth.models import AbstractUser
from django.db import models


class User(AbstractUser):
    class Role(models.TextChoices):
        ADMIN = "admin", "Admin"
        RIDER = "rider", "Rider"
        DRIVER = "driver", "Driver"

    id = models.AutoField(primary_key=True, db_column="id_user")

    role = models.CharField(
        max_length=20,
        choices=Role.choices,
        default=Role.RIDER,
        db_index=True,
        help_text="Drives admin-only API access control.",
    )

    email = models.EmailField(
        unique=True,
        db_index=True,
        help_text="Used as a filter key on the Ride List API (rider email).",
    )

    phone_number = models.CharField(max_length=20, blank=True)

    class Meta:
        db_table = "user"
        indexes = [
            models.Index(fields=["role"], name="user_role_idx"),
        ]

    def __str__(self):
        return f"{self.first_name} {self.last_name} ({self.role})".strip()
