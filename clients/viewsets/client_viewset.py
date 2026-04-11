from rest_framework.decorators import action
from rest_framework.generics import get_object_or_404
from rest_framework.response import Response
from rest_framework import status, mixins, viewsets

from clients.services.client_service import ClientService, ClientNotFound
from clients.serializers.client_serializer import ClientSerializer, ClientVisitSerializer
from clients.selectors.client_selector import ClientSelector


class ClientViewSet(mixins.ListModelMixin,
    mixins.RetrieveModelMixin,
    mixins.CreateModelMixin,
    viewsets.GenericViewSet,):

    serializer_class = ClientSerializer
    client_selector = ClientSelector()
    #permission_classes = [DjangoModelPermissions]

    def get_queryset(self):
        return self.client_selector.get_clients_queryset(
            email=self.request.query_params.get("email", None)
        )

    @action(detail=False, methods=["get"], url_path="visits_by_clients")
    def get_clients_visits_queryset(self, request):
        clients = self.client_selector.get_clients_visits_queryset()

        serializer = ClientVisitSerializer(clients, many=True)
        return Response(serializer.data)

    def retrieve(self, request, *args, **kwargs):
        client = get_object_or_404(self.client_selector.get_clients_queryset(),
                                   pk=kwargs["pk"])

        serializer = ClientSerializer(client)
        return Response(serializer.data)

    def create(self, request, *args, **kwargs):
        serializer = self.serializer_class(data=request.data)
        serializer.is_valid(raise_exception=True)

        created_client = ClientService().create_client(serializer.validated_data)

        out = self.serializer_class(created_client)
        return Response({"detail": f"Client created: {out.data}"}, status=status.HTTP_201_CREATED)
