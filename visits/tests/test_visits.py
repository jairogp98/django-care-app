from datetime import datetime
from unittest.mock import MagicMock, patch

import pytest
from django.contrib.auth import get_user_model
from django.core.exceptions import ValidationError
from django.urls import reverse
from django.utils import timezone
from rest_framework.test import APIClient

from visits.models.models import Visit, VisitNote, VisitTask
from visits.selectors.selectors import VisitSelector
from visits.serializers.serializers import VisitWriteSerializer
from visits.services.exceptions import (
    CaregiverScheduleConflictError,
    VisitAlreadyCancelledError,
    VisitHasPendingMandatoryTasksError,
    VisitTaskAlreadyCompletedError,
)
from visits.services.services import VisitService
from visits.viewsets.viewsets import VisitViewSet


def test_import_visits_views_and_admin():
    import visits.admin  # noqa: F401
    import visits.views  # noqa: F401


@pytest.mark.django_db
class TestVisitService:
    def test_create_visit_success(self, client, caregiver):
        start = timezone.now() + timezone.timedelta(days=1)
        end = start + timezone.timedelta(hours=1)
        visit = VisitService.create_visit(
            client=client,
            assigned_caregiver=caregiver,
            visit_type=Visit.Type.PHYSIOTHERAPY,
            scheduled_start=start,
            scheduled_end=end,
            summary="Resumen",
            tasks=[
                {"name": "T1", "order": 1, "is_mandatory": True},
                {"name": "T2", "order": 2},
            ],
        )
        assert visit.pk is not None
        assert visit.summary == "Resumen"
        assert visit.tasks.count() == 2
        t2 = visit.tasks.get(order=2)
        assert t2.is_mandatory is True  # default en dict

    def test_create_visit_without_tasks_bulk_create_skipped(self, client, caregiver):
        start = timezone.now() + timezone.timedelta(days=2)
        end = start + timezone.timedelta(hours=1)
        visit = VisitService.create_visit(
            client=client,
            assigned_caregiver=caregiver,
            visit_type=Visit.Type.CHECKUP,
            scheduled_start=start,
            scheduled_end=end,
        )
        assert visit.tasks.count() == 0

    def test_create_visit_invalid_range_raises(self, client, caregiver):
        start = timezone.now() + timezone.timedelta(days=1)
        end = start
        with pytest.raises(ValueError, match="scheduled_end"):
            VisitService.create_visit(
                client=client,
                assigned_caregiver=caregiver,
                visit_type=Visit.Type.HYGIENE,
                scheduled_start=start,
                scheduled_end=end,
            )

    def test_create_visit_overlap_raises(self, client, caregiver, visit_factory):
        base = timezone.now() + timezone.timedelta(days=3)
        visit_factory(
            scheduled_start=base,
            scheduled_end=base + timezone.timedelta(hours=2),
            status=Visit.Status.SCHEDULED,
        )
        with pytest.raises(CaregiverScheduleConflictError):
            VisitService.create_visit(
                client=client,
                assigned_caregiver=caregiver,
                visit_type=Visit.Type.MEDICATION,
                scheduled_start=base + timezone.timedelta(hours=1),
                scheduled_end=base + timezone.timedelta(hours=3),
            )

    def test_create_visit_overlap_in_progress_raises(self, client, caregiver, visit_factory):
        base = timezone.now() + timezone.timedelta(days=4)
        visit_factory(
            scheduled_start=base,
            scheduled_end=base + timezone.timedelta(hours=2),
            status=Visit.Status.IN_PROGRESS,
        )
        with pytest.raises(CaregiverScheduleConflictError):
            VisitService.create_visit(
                client=client,
                assigned_caregiver=caregiver,
                visit_type=Visit.Type.MEDICATION,
                scheduled_start=base + timezone.timedelta(minutes=30),
                scheduled_end=base + timezone.timedelta(hours=2, minutes=30),
            )

    def test_create_visit_no_conflict_when_completed(self, client, caregiver, visit_factory):
        base = timezone.now() + timezone.timedelta(days=5)
        visit_factory(
            scheduled_start=base,
            scheduled_end=base + timezone.timedelta(hours=2),
            status=Visit.Status.COMPLETED,
        )
        v = VisitService.create_visit(
            client=client,
            assigned_caregiver=caregiver,
            visit_type=Visit.Type.MEDICATION,
            scheduled_start=base + timezone.timedelta(hours=1),
            scheduled_end=base + timezone.timedelta(hours=3),
        )
        assert v.status == Visit.Status.SCHEDULED

    def test_add_note(self, visit_factory, caregiver):
        visit = visit_factory()
        note = VisitService.add_note(visit=visit, author=caregiver, body="Nota")
        assert note.body == "Nota"
        assert note.author_id == caregiver.id

    def test_complete_task(self, visit_factory):
        visit = visit_factory()
        task = VisitTask.objects.create(
            visit=visit, name="x", order=1, is_mandatory=True
        )
        updated = VisitService.complete_task(task=task)
        assert updated.is_completed is True
        assert updated.completed_at is not None

    def test_complete_task_already_done_raises(self, visit_factory):
        visit = visit_factory()
        task = VisitTask.objects.create(
            visit=visit,
            name="x",
            order=1,
            is_completed=True,
            completed_at=timezone.now(),
        )
        with pytest.raises(VisitTaskAlreadyCompletedError):
            VisitService.complete_task(task=task)

    def test_complete_visit_success(self, visit_factory):
        visit = visit_factory()
        VisitTask.objects.create(
            visit=visit, name="m", order=1, is_mandatory=True, is_completed=True
        )
        VisitTask.objects.create(
            visit=visit, name="o", order=2, is_mandatory=False, is_completed=False
        )
        out = VisitService.complete_visit(visit=visit)
        assert out.status == Visit.Status.COMPLETED

    def test_complete_visit_cancelled_raises(self, visit_factory):
        visit = visit_factory(status=Visit.Status.CANCELLED)
        with pytest.raises(ValueError, match="cancelada"):
            VisitService.complete_visit(visit=visit)

    def test_complete_visit_pending_mandatory_raises(self, visit_factory):
        visit = visit_factory()
        VisitTask.objects.create(
            visit=visit, name="m", order=1, is_mandatory=True, is_completed=False
        )
        with pytest.raises(VisitHasPendingMandatoryTasksError):
            VisitService.complete_visit(visit=visit)

    def test_cancel_visit_success(self, visit_factory):
        visit = visit_factory()
        out = VisitService.cancel_visit(visit=visit)
        assert out.status == Visit.Status.CANCELLED

    def test_cancel_visit_already_cancelled_raises(self, visit_factory):
        visit = visit_factory(status=Visit.Status.CANCELLED)
        with pytest.raises(VisitAlreadyCancelledError):
            VisitService.cancel_visit(visit=visit)

    def test_cancel_visit_completed_raises(self, visit_factory):
        visit = visit_factory(status=Visit.Status.COMPLETED)
        with pytest.raises(ValueError, match="completada"):
            VisitService.cancel_visit(visit=visit)


@pytest.mark.django_db
class TestVisitModel:
    def test_str_and_clean(self, visit_factory, client):
        visit = visit_factory()
        assert "Visit #" in str(visit)
        assert str(client) in str(visit)

        visit.scheduled_end = visit.scheduled_start
        with pytest.raises(ValidationError):
            visit.full_clean()

        task = VisitTask.objects.create(visit=visit, name="n", order=1)
        assert task.name in str(task)

        note = VisitNote.objects.create(visit=visit, author=visit.assigned_caregiver, body="b")
        assert str(note.pk) in str(note)


@pytest.mark.django_db
class TestVisitSelector:
    def test_get_visits_queryset_filters_and_afternoon(self, visit_factory, caregiver):
        v_am = visit_factory(
            scheduled_start=timezone.make_aware(
                datetime(2030, 1, 1, 10, 0, 0), timezone.get_current_timezone()
            ),
            scheduled_end=timezone.make_aware(
                datetime(2030, 1, 1, 11, 0, 0), timezone.get_current_timezone()
            ),
        )
        v_pm = visit_factory(
            scheduled_start=timezone.make_aware(
                datetime(2030, 1, 2, 14, 0, 0), timezone.get_current_timezone()
            ),
            scheduled_end=timezone.make_aware(
                datetime(2030, 1, 2, 15, 0, 0), timezone.get_current_timezone()
            ),
        )
        VisitTask.objects.create(visit=v_am, name="t", order=1, is_completed=True)

        qs = VisitSelector.get_visits_queryset()
        rows = {v.id: v for v in qs}
        assert rows[v_am.id].afternoon_visit is False
        assert rows[v_pm.id].afternoon_visit is True
        assert rows[v_am.id].total_tasks == 1
        assert rows[v_am.id].completed_tasks == 1

        f1 = VisitSelector.get_visits_queryset(client_id=v_am.client_id)
        assert set(f1.values_list("id", flat=True)) == {v_am.id, v_pm.id}

        f2 = VisitSelector.get_visits_queryset(caregiver_id=caregiver.id)
        assert f2.count() >= 2

        f3 = VisitSelector.get_visits_queryset(status=Visit.Status.SCHEDULED)
        assert v_am.id in f3.values_list("id", flat=True)

        f4 = VisitSelector.get_visits_queryset(
            client_id=v_am.client_id,
            caregiver_id=caregiver.id,
            status=Visit.Status.SCHEDULED,
        )
        assert v_am.id in f4.values_list("id", flat=True)

    def test_get_visit_detail_queryset_prefetch(self, visit_factory, caregiver):
        visit = visit_factory()
        VisitTask.objects.create(visit=visit, name="a", order=1)
        VisitNote.objects.create(visit=visit, author=caregiver, body="n")
        obj = VisitSelector.get_visit_detail_queryset().get(pk=visit.pk)
        assert obj.total_tasks >= 1
        assert len(list(obj.tasks.all())) >= 1
        assert len(list(obj.notes.all())) >= 1

    def test_get_upcoming_visits_for_client_queryset(self, visit_factory):
        visit = visit_factory(
            status=Visit.Status.SCHEDULED,
            scheduled_start=timezone.now() + timezone.timedelta(days=10),
        )
        qs = VisitSelector.get_upcoming_visits_for_client_queryset(
            client_id=visit.client_id
        )
        assert visit.id in qs.values_list("id", flat=True)

    def test_get_tasks_by_caregiver(self, visit_factory, caregiver):
        visit = visit_factory()
        t = VisitTask.objects.create(visit=visit, name="job", order=1)
        qs = VisitSelector.get_tasks_by_caregiver(caregiver_id=caregiver.id)
        assert t.id in qs.values_list("id", flat=True)
        qs_none = VisitSelector.get_tasks_by_caregiver(caregiver_id=None)
        assert qs_none.count() == 0


@pytest.mark.django_db
class TestVisitWriteSerializer:
    def test_validate_scheduled_range(self, client, caregiver):
        start = timezone.now()
        end = start - timezone.timedelta(hours=1)
        ser = VisitWriteSerializer(
            data={
                "client_id": client.pk,
                "assigned_caregiver_id": caregiver.pk,
                "visit_type": Visit.Type.PHYSIOTHERAPY,
                "scheduled_start": start,
                "scheduled_end": end,
            }
        )
        assert ser.is_valid() is False
        assert "scheduled_end" in ser.errors


@pytest.mark.django_db
class TestVisitViewSet:
    @pytest.fixture
    def superuser(self):
        User = get_user_model()
        return User.objects.create_superuser(
            username="su_visits",
            password="pw",
            email="su@v.test",
        )

    @pytest.fixture
    def api(self):
        return APIClient()

    def test_list_retrieve_create_flow(self, api, superuser, client, caregiver):
        api.force_authenticate(user=superuser)
        start = timezone.now() + timezone.timedelta(days=20)
        end = start + timezone.timedelta(hours=1)
        create_url = reverse("visit-list")
        resp = api.post(
            create_url,
            {
                "client_id": client.pk,
                "assigned_caregiver_id": caregiver.pk,
                "visit_type": Visit.Type.PHYSIOTHERAPY,
                "scheduled_start": start.isoformat(),
                "scheduled_end": end.isoformat(),
                "summary": "s",
                "tasks": [{"name": "do", "order": 1}],
            },
            format="json",
        )
        assert resp.status_code == 201
        vid = resp.data["id"]

        r_list = api.get(create_url)
        assert r_list.status_code == 200
        assert len(r_list.data) >= 1

        r_detail = api.get(reverse("visit-detail", args=[vid]))
        assert r_detail.status_code == 200
        assert r_detail.data["id"] == vid

    def test_create_conflict_and_bad_dates(self, api, superuser, client, caregiver, visit_factory):
        api.force_authenticate(user=superuser)
        base = timezone.now() + timezone.timedelta(days=30)
        visit_factory(
            scheduled_start=base,
            scheduled_end=base + timezone.timedelta(hours=2),
            status=Visit.Status.SCHEDULED,
        )
        url = reverse("visit-list")
        r_conflict = api.post(
            url,
            {
                "client_id": client.pk,
                "assigned_caregiver_id": caregiver.pk,
                "visit_type": Visit.Type.HYGIENE,
                "scheduled_start": (base + timezone.timedelta(hours=1)).isoformat(),
                "scheduled_end": (base + timezone.timedelta(hours=3)).isoformat(),
            },
            format="json",
        )
        assert r_conflict.status_code == 400

        r_bad = api.post(
            url,
            {
                "client_id": client.pk,
                "assigned_caregiver_id": caregiver.pk,
                "visit_type": Visit.Type.HYGIENE,
                "scheduled_start": base.isoformat(),
                "scheduled_end": base.isoformat(),
            },
            format="json",
        )
        assert r_bad.status_code == 400

    def test_create_value_error_from_service(self, api, superuser, client, caregiver):
        api.force_authenticate(user=superuser)
        start = timezone.now() + timezone.timedelta(days=40)
        end = start + timezone.timedelta(hours=1)
        with patch.object(VisitService, "create_visit", side_effect=ValueError("error interno")):
            r = api.post(
                reverse("visit-list"),
                {
                    "client_id": client.pk,
                    "assigned_caregiver_id": caregiver.pk,
                    "visit_type": Visit.Type.HYGIENE,
                    "scheduled_start": start.isoformat(),
                    "scheduled_end": end.isoformat(),
                },
                format="json",
            )
        assert r.status_code == 400
        assert "error interno" in str(r.data)

    def test_add_note_complete_task_complete_cancel(self, api, superuser, visit_factory, caregiver):
        api.force_authenticate(user=superuser)
        visit = visit_factory()
        task = VisitTask.objects.create(visit=visit, name="t", order=1, is_mandatory=True)

        r_note = api.post(
            reverse("visit-add-note", args=[visit.pk]),
            {"body": "hola"},
            format="json",
        )
        assert r_note.status_code == 201

        r_task = api.post(
            reverse("visit-complete-task", args=[visit.pk]),
            {"task_id": task.pk},
            format="json",
        )
        assert r_task.status_code == 200

        r_task_again = api.post(
            reverse("visit-complete-task", args=[visit.pk]),
            {"task_id": task.pk},
            format="json",
        )
        assert r_task_again.status_code == 400

        r_done = api.post(reverse("visit-complete", args=[visit.pk]), {}, format="json")
        assert r_done.status_code == 200

        visit2 = visit_factory()
        VisitTask.objects.create(
            visit=visit2, name="pend", order=1, is_mandatory=True, is_completed=False
        )
        r_pending = api.post(reverse("visit-complete", args=[visit2.pk]), {}, format="json")
        assert r_pending.status_code == 400

        r_cancel = api.post(reverse("visit-cancel", args=[visit2.pk]), {}, format="json")
        assert r_cancel.status_code == 200

        r_cancel_again = api.post(reverse("visit-cancel", args=[visit2.pk]), {}, format="json")
        assert r_cancel_again.status_code == 400

        visit3 = visit_factory(status=Visit.Status.COMPLETED)
        r_cancel_done = api.post(reverse("visit-cancel", args=[visit3.pk]), {}, format="json")
        assert r_cancel_done.status_code == 400

    def test_complete_cancelled_visit(self, api, superuser, visit_factory):
        api.force_authenticate(user=superuser)
        visit = visit_factory(status=Visit.Status.CANCELLED)
        r = api.post(reverse("visit-complete", args=[visit.pk]), {}, format="json")
        assert r.status_code == 400

    def test_list_tasks_by_caregiver(self, api, superuser, visit_factory, caregiver):
        api.force_authenticate(user=superuser)
        visit = visit_factory()
        VisitTask.objects.create(visit=visit, name="x", order=1)
        url = reverse("visit-list-tasks-by-caregiver")
        r = api.get(url, {"caregiver_id": caregiver.pk})
        assert r.status_code == 200
        assert isinstance(r.data, list)
        r_empty = api.get(url)
        assert r_empty.status_code == 200

    def test_retrieve_404(self, api, superuser):
        api.force_authenticate(user=superuser)
        r = api.get(reverse("visit-detail", args=[99999]))
        assert r.status_code == 404

    def test_get_serializer_class_default_is_detail(self):
        view = VisitViewSet()
        view.action = "update"
        assert view.get_serializer_class().__name__ == "VisitDetailSerializer"

    def test_update_method_runs(self, superuser):
        request = MagicMock()
        request.data = {}
        view = VisitViewSet()
        with patch.object(VisitViewSet, "get_serializer") as mock_gs:
            mock_serializer = MagicMock()
            mock_serializer.is_valid.return_value = True
            mock_gs.return_value = mock_serializer
            view.update(request, pk=1)


@pytest.mark.django_db
def test_visit_factory_creates_scheduled(visit_factory):
    visit = visit_factory(summary="Esto es un summary")
    assert visit.status == "scheduled"
