from django.contrib.auth import get_user_model
from rest_framework import serializers

from clients.models.models import Client
from ..models.models import Visit, VisitTask, VisitNote

User = get_user_model()

class VisitTaskSerializer(serializers.ModelSerializer):
    class Meta:
        model = VisitTask
        fields = (
            "id",
            "name",
            "order",
            "is_mandatory",
            "is_completed",
            "completed_at",
        )

class VisitTaskInputSerializer(serializers.Serializer):
    name = serializers.CharField(max_length=255)
    order = serializers.IntegerField(min_value=1)
    is_mandatory = serializers.BooleanField(default=True)

class VisitWriteSerializer(serializers.Serializer):
    client_id = serializers.PrimaryKeyRelatedField(
        queryset=Client.objects.all(),
        source="client",
    )
    assigned_caregiver_id = serializers.PrimaryKeyRelatedField(
        queryset=User.objects.all(),
        source="assigned_caregiver",
    )
    visit_type = serializers.ChoiceField(choices=Visit.Type.choices)
    scheduled_start = serializers.DateTimeField()
    scheduled_end = serializers.DateTimeField()
    summary = serializers.CharField(required=False, allow_blank=True, default="")
    tasks = VisitTaskInputSerializer(many=True, required=False)

    def validate(self, attrs):
        if attrs["scheduled_end"] <= attrs["scheduled_start"]:
            raise serializers.ValidationError(
                {"scheduled_end": "scheduled_end debe ser mayor que scheduled_start."}
            )
        return attrs


class VisitListSerializer(serializers.ModelSerializer):
    client = serializers.StringRelatedField()
    assigned_caregiver = serializers.StringRelatedField()
    total_tasks = serializers.IntegerField(read_only=True)
    completed_tasks = serializers.IntegerField(read_only=True)

    class Meta:
        model = Visit
        fields = (
            "id",
            "client",
            "assigned_caregiver",
            "visit_type",
            "status",
            "scheduled_start",
            "scheduled_end",
            "total_tasks",
            "completed_tasks",
        )

class VisitNoteSerializer(serializers.ModelSerializer):
    author = serializers.StringRelatedField()

    class Meta:
        model = VisitNote
        fields = (
            "id",
            "author",
            "body",
            "created_at",
        )

class VisitDetailSerializer(serializers.ModelSerializer):
    client = serializers.StringRelatedField()
    assigned_caregiver = serializers.StringRelatedField()
    tasks = VisitTaskSerializer(many=True, read_only=True)
    notes = VisitNoteSerializer(many=True, read_only=True)
    total_tasks = serializers.IntegerField(read_only=True)
    completed_tasks = serializers.IntegerField(read_only=True)

    class Meta:
        model = Visit
        fields = (
            "id",
            "client",
            "assigned_caregiver",
            "visit_type",
            "status",
            "scheduled_start",
            "scheduled_end",
            "summary",
            "total_tasks",
            "completed_tasks",
            "tasks",
            "notes",
            "created_at",
            "updated_at",
        )


class VisitAddNoteSerializer(serializers.Serializer):
    body = serializers.CharField()


class VisitCompleteTaskSerializer(serializers.Serializer):
    task_id = serializers.IntegerField(min_value=1)