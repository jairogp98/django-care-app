from typing import Iterable
from clients.models.models import Client
from django.shortcuts import get_object_or_404


class ClientSelector:

    @staticmethod
    def list_clients() -> Iterable[Client]:
        return Client.objects.all()

    @staticmethod
    def client_by_id(pk) -> Client:
       return get_object_or_404(Client, pk=pk)


