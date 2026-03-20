from django.core.exceptions import ObjectDoesNotExist
from django.db import transaction
from django.utils import timezone

from ..models.models import Visit, VisitTask, VisitNote

class VisitService:
    class CaregiverScheduleConflictError(Exception):
        pass

    class VisitTaskAlreadyCompletedError(Exception):
        pass

    class VisitHasPendingMandatoryTasksError(Exception):
        pass

    class VisitAlreadyCancelledError(Exception):
        pass

    @staticmethod
    def create_visit(
        *,
        client,
        assigned_caregiver,
        visit_type,
        scheduled_start,
        scheduled_end,
        summary="",
        tasks=None,
    ):
        if scheduled_end <= scheduled_start:
            raise ValueError("scheduled_end debe ser mayor que scheduled_start.")

        overlapping_visit_exists = Visit.objects.filter(
            assigned_caregiver=assigned_caregiver,
            status__in=[Visit.Status.SCHEDULED, Visit.Status.IN_PROGRESS],
            scheduled_start__lt=scheduled_end,
            scheduled_end__gt=scheduled_start,
        ).exists()

        if overlapping_visit_exists:
            raise CaregiverScheduleConflictError(
                "El cuidador ya tiene otra visita en ese rango horario."
            )

        tasks = tasks or []

        with transaction.atomic():
            visit = Visit.objects.create(
                client=client,
                assigned_caregiver=assigned_caregiver,
                visit_type=visit_type,
                scheduled_start=scheduled_start,
                scheduled_end=scheduled_end,
                summary=summary,
            )

            task_objects = [
                VisitTask(
                    visit=visit,
                    name=task["name"],
                    order=task["order"],
                    is_mandatory=task.get("is_mandatory", True),
                )
                for task in tasks
            ]

            if task_objects:
                VisitTask.objects.bulk_create(task_objects)

        return visit

    @staticmethod
    def add_note(*, visit, author, body):
        return VisitNote.objects.create(
            visit=visit,
            author=author,
            body=body,
        )

    @staticmethod
    def complete_task(*, task):
        if task.is_completed:
            raise VisitTaskAlreadyCompletedError("La tarea ya estaba completada.")

        task.is_completed = True
        task.completed_at = timezone.now()
        task.save(update_fields=["is_completed", "completed_at"])

        return task

    @staticmethod
    def complete_visit(*, visit):
        if visit.status == Visit.Status.CANCELLED:
            raise ValueError("No puedes completar una visita cancelada.")

        has_pending_mandatory_tasks = visit.tasks.filter(
            is_mandatory=True,
            is_completed=False,
        ).exists()

        if has_pending_mandatory_tasks:
            raise VisitHasPendingMandatoryTasksError(
                "No puedes completar la visita si faltan tareas obligatorias."
            )

        visit.status = Visit.Status.COMPLETED
        visit.save(update_fields=["status", "updated_at"])

        return visit

    @staticmethod
    def cancel_visit(*, visit):
        if visit.status == Visit.Status.CANCELLED:
            raise VisitAlreadyCancelledError("La visita ya estaba cancelada.")

        if visit.status == Visit.Status.COMPLETED:
            raise ValueError("No puedes cancelar una visita ya completada.")

        visit.status = Visit.Status.CANCELLED
        visit.save(update_fields=["status", "updated_at"])

        return visit