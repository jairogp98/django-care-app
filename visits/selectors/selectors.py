from django.db.models import Count, Prefetch, Q, Case, When, Value, BooleanField, Min, Max

from ..models.models import Visit, VisitTask, VisitNote

class VisitSelector:

    @staticmethod
    def get_visits_queryset(*, client_id=None, caregiver_id=None, status=None):
        queryset = (
            Visit.objects.select_related(
                "client",
                "assigned_caregiver",
            )
            .annotate(
                total_tasks=Count("tasks", distinct=True),
                completed_tasks=Count(
                    "tasks",
                    filter=Q(tasks__is_completed=True),
                    distinct=True,
                ),
                afternoon_visit=Case(
                            When(
                                    scheduled_start__hour__gte=12,
                                    then=Value(True),
                                    ),
                                default=Value(False),
                                output_field=BooleanField(),
                            )
            )
        )

        if client_id:
            queryset = queryset.filter(client_id=client_id)

        if caregiver_id:
            queryset = queryset.filter(assigned_caregiver_id=caregiver_id)

        if status:
            queryset = queryset.filter(status=status)

        return queryset

    @staticmethod
    def get_visit_detail_queryset():
        return (
            Visit.objects.select_related(
                "client",
                "assigned_caregiver",
            )
            .prefetch_related(
                Prefetch(
                    "tasks",
                    queryset=VisitTask.objects.order_by("order", "id"),
                ),
                Prefetch(
                    "notes",
                    queryset=VisitNote.objects.select_related("author").order_by("-created_at"),
                ),
            )
            .annotate(
                total_tasks=Count("tasks", distinct=True),
                completed_tasks=Count(
                    "tasks",
                    filter=Q(tasks__is_completed=True),
                    distinct=True,
                ),
            )
        )

    @staticmethod
    def get_upcoming_visits_for_client_queryset(*, client_id):
        return (
            Visit.objects.select_related("assigned_caregiver")
            .filter(
                client_id=client_id,
                status=Visit.Status.SCHEDULED,
            )
            .order_by("scheduled_start")
        )

    @staticmethod
    def get_tasks_by_caregiver(*, caregiver_id):
        return (
            VisitTask.objects
            .select_related("visit__assigned_caregiver")
            .filter(visit__assigned_caregiver_id=caregiver_id)
        )