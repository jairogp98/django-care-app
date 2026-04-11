from typing import Iterable

from django.db.models import F, Count

from clients.models.models import Client
from django.shortcuts import get_object_or_404


class ClientSelector:

    @staticmethod
    def get_clients_queryset(*, email=None):
        queryset = Client.objects.filter(is_active=True)
        if email:
            queryset = queryset.filter(email=email)
        return queryset


    @staticmethod
    def get_clients_visits_queryset():
        queryset = Client.objects.prefetch_related("visits").filter(is_active=True).annotate(
            total_visits = Count("visits")
        )
        return queryset