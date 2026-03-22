from django.shortcuts import get_object_or_404
from rest_framework import mixins, status, viewsets
from rest_framework.decorators import action
from rest_framework.exceptions import ValidationError
from rest_framework.response import Response

from ..selectors.selectors import VisitSelector
from ..services.services import VisitService
from ..models.models import Visit, VisitTask
from ..serializers.serializers import (
    VisitAddNoteSerializer,
    VisitCompleteTaskSerializer,
    VisitDetailSerializer,
    VisitListSerializer,
    VisitNoteSerializer,
    VisitTaskSerializer,
    VisitWriteSerializer,
)


class VisitViewSet(
    mixins.ListModelMixin,
    mixins.RetrieveModelMixin,
    mixins.CreateModelMixin,
    viewsets.GenericViewSet,
):
    queryset = Visit.objects.none()
    visit_selector = VisitSelector()
    visit_service = VisitService()

    def get_queryset(self):
        return self.visit_selector.get_visits_queryset(
            client_id=self.request.query_params.get("client_id"),
            caregiver_id=self.request.query_params.get("assigned_caregiver_id"),
            status=self.request.query_params.get("status"),
        )

    def get_serializer_class(self):
        if self.action == "list":
            return VisitListSerializer
        if self.action == "retrieve":
            return VisitDetailSerializer
        if self.action == "create":
            return VisitWriteSerializer
        if self.action == "add_note":
            return VisitAddNoteSerializer
        if self.action == "complete_task":
            return VisitCompleteTaskSerializer
        return VisitDetailSerializer

    def retrieve(self, request, *args, **kwargs):
        visit = get_object_or_404(
            self.visit_selector.get_visit_detail_queryset(),
            pk=kwargs["pk"],
        )
        serializer = self.get_serializer(visit)
        return Response(serializer.data)

    def update(self, request, *args, **kwargs):
        serializer = self.get_serializer(data=request.data)
        serializer.is_valid(raise_exception=True)
        #TODO

    def create(self, request, *args, **kwargs):
        serializer = self.get_serializer(data=request.data)
        serializer.is_valid(raise_exception=True)

        try:
            visit = self.visit_service.create_visit(**serializer.validated_data)
        except self.visit_service.CaregiverScheduleConflictError as exc:
            raise ValidationError({"detail": str(exc)})
        except ValueError as exc:
            raise ValidationError({"detail": str(exc)})

        visit = get_object_or_404(
            self.visit_selector.get_visit_detail_queryset(),
            pk=visit.pk,
        )
        output = VisitDetailSerializer(visit)
        return Response(output.data, status=status.HTTP_201_CREATED)

    @action(detail=True, methods=["post"], url_path="add-note")
    def add_note(self, request, pk=None):
        visit = get_object_or_404(Visit, pk=pk)
        serializer = self.get_serializer(data=request.data)
        serializer.is_valid(raise_exception=True)

        note = self.visit_service.add_note(
            visit=visit,
            author=request.user,
            body=serializer.validated_data["body"],
        )
        return Response(VisitNoteSerializer(note).data, status=status.HTTP_201_CREATED)

    @action(detail=True, methods=["post"], url_path="complete-task")
    def complete_task(self, request, pk=None):
        visit = get_object_or_404(Visit, pk=pk)
        serializer = self.get_serializer(data=request.data)
        serializer.is_valid(raise_exception=True)

        task = get_object_or_404(
            VisitTask,
            pk=serializer.validated_data["task_id"],
            visit=visit,
        )

        try:
            task = self.visit_service.complete_task(task=task)
        except self.visit_service.VisitTaskAlreadyCompletedError as exc:
            raise ValidationError({"detail": str(exc)})

        return Response(VisitTaskSerializer(task).data, status=status.HTTP_200_OK)

    @action(detail=True, methods=["post"], url_path="complete")
    def complete(self, request, pk=None):
        visit = get_object_or_404(Visit.objects.prefetch_related("tasks"), pk=pk)

        try:
            visit = self.visit_service.complete_visit(visit=visit)
        except self.visit_service.VisitHasPendingMandatoryTasksError as exc:
            raise ValidationError({"detail": str(exc)})
        except ValueError as exc:
            raise ValidationError({"detail": str(exc)})

        visit = get_object_or_404(self.visit_selector.get_visit_detail_queryset(), pk=visit.pk)
        return Response(VisitDetailSerializer(visit).data, status=status.HTTP_200_OK)

    @action(detail=True, methods=["post"], url_path="cancel")
    def cancel(self, request, pk=None):
        visit = get_object_or_404(Visit, pk=pk)

        try:
            visit = self.visit_service.cancel_visit(visit=visit)
        except self.visit_service.VisitAlreadyCancelledError as exc:
            raise ValidationError({"detail": str(exc)})
        except ValueError as exc:
            raise ValidationError({"detail": str(exc)})

        visit = get_object_or_404(self.visit_selector.get_visit_detail_queryset(), pk=visit.pk)
        return Response(VisitDetailSerializer(visit).data, status=status.HTTP_200_OK)

    @action(detail=False, methods=["get"], url_path="tasks_by_caregiver")
    def list_tasks_by_caregiver(self, request, *args, **kwargs):
        caregiver_id = request.query_params.get("caregiver_id", None)
        queryset = self.visit_selector.get_tasks_by_caregiver(caregiver_id=caregiver_id)
        serializer = VisitTaskSerializer(queryset, many=True)

        return Response(serializer.data)