from rest_framework.status import HTTP_400_BAD_REQUEST
from rest_framework.viewsets import ViewSet, ModelViewSet
from rest_framework.response import Response
from rest_framework import status

from clients.services.client_service import ClientService, ClientNotFound
from clients.serializers.client_serializer import ClientSerializer
from clients.selectors.client_selector import ClientSelector


class ClientViewSet(ViewSet):

    serializer_class = ClientSerializer

    def list(self, request):

        clients = ClientSelector.list_clients()
        serializer = ClientSerializer(clients, many=True)
        return Response(serializer.data)

    def retrieve(self, request, pk):
        try:
            client = ClientSelector.client_by_id(pk)
        except ClientNotFound:
            return Response(
                {"detail": "Client not found"},
                status=status.HTTP_404_NOT_FOUND,
            )

        serializer = ClientSerializer(client)
        return Response(serializer.data)

    def create(self, request, *args, **kwargs):
        serializer = self.serializer_class(data=request.data)
        serializer.is_valid(raise_exception=True)

        created_client = ClientService().create_client(serializer.validated_data)

        out = self.serializer_class(created_client)
        return Response({"detail": f"Client created: {out.data}"}, status=status.HTTP_201_CREATED)
