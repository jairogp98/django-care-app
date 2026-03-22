from django.conf import settings
from django.core.exceptions import ValidationError
from django.db import models

from clients.models.models import Client


class Visit(models.Model):
    class Status(models.TextChoices):
        SCHEDULED = "scheduled", "Scheduled"
        IN_PROGRESS = "in_progress", "In progress"
        COMPLETED = "completed", "Completed"
        CANCELLED = "cancelled", "Cancelled"

    class Type(models.TextChoices):
        MEDICATION = "medication", "Medication"
        HYGIENE = "hygiene", "Hygiene"
        PHYSIOTHERAPY = "physiotherapy", "Physiotherapy"
        CHECKUP = "checkup", "Checkup"
        COMPANIONSHIP = "companionship", "Companionship"

    client = models.ForeignKey(
        Client,
        on_delete=models.CASCADE,
        related_name="visits",
    )
    assigned_caregiver = models.ForeignKey(
        settings.AUTH_USER_MODEL,
        on_delete=models.PROTECT,
        related_name="assigned_caregiver",
    )
    visit_type = models.CharField(
        max_length=32,
        choices=Type.choices,
    )
    scheduled_start = models.DateTimeField(db_index=True)
    scheduled_end = models.DateTimeField()
    status = models.CharField(
        max_length=20,
        choices=Status.choices,
        default=Status.SCHEDULED,
        db_index=True,
    )
    summary = models.TextField(blank=True)

    created_at = models.DateTimeField(auto_now_add=True)
    updated_at = models.DateTimeField(auto_now=True)

    class Meta:
        ordering = ("-scheduled_start",)
        indexes = [
            models.Index(fields=["client", "scheduled_start"]),
            models.Index(fields=["assigned_caregiver", "scheduled_start"]),
            models.Index(fields=["status", "scheduled_start"]),
        ]

    def clean(self):
        if self.scheduled_end <= self.scheduled_start:
            raise ValidationError(
                {"scheduled_end": "scheduled_end debe ser mayor que scheduled_start."}
            )

    def __str__(self):
        return f"Visit #{self.pk} - {self.client}"


class VisitTask(models.Model):
    visit = models.ForeignKey(
        Visit,
        on_delete=models.CASCADE,
        related_name="tasks",
    )
    name = models.CharField(max_length=255)
    order = models.PositiveSmallIntegerField(default=1)
    is_mandatory = models.BooleanField(default=True)
    is_completed = models.BooleanField(default=False)
    completed_at = models.DateTimeField(null=True, blank=True)

    class Meta:
        ordering = ("order", "id")
        constraints = [
            models.UniqueConstraint(
                fields=["visit", "order"],
                name="unique_task_order_per_visit",
            )
        ]

    def __str__(self):
        return f"{self.pk} - {self.name}"


class VisitNote(models.Model):
    visit = models.ForeignKey(
        Visit,
        on_delete=models.CASCADE,
        related_name="notes",
    )
    author = models.ForeignKey(
        settings.AUTH_USER_MODEL,
        on_delete=models.PROTECT,
        related_name="notes_author",
    )
    body = models.TextField()
    created_at = models.DateTimeField(auto_now_add=True)

    class Meta:
        ordering = ("-created_at",)

    def __str__(self):
        return f"Note #{self.pk} for Visit #{self.visit_id}"
