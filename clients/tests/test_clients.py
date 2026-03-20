import pytest
from rest_framework.test import APIClient
from django.urls import reverse

from clients.models.models import Client


@pytest.mark.django_db
class TestClientViewSet:
    def setup_method(self):
        self.api_client = APIClient()

    def test_list_clients_returns_clients(self):
        """
        GET /api/clients/
        """
        Client.objects.create(
            name="Acme Corp",
            email="contact@acme.com"
        )
        Client.objects.create(
            name="Globex",
            email="hello@globex.com"
        )

        url = reverse("client-list")
        response = self.api_client.get(url)

        assert response.status_code == 200
        assert isinstance(response.data, list)
        assert len(response.data) == 2

    def test_retrieve_client_by_id(self):
        """
        GET /api/clients/{id}/
        """
        client = Client.objects.create(
            name="Acme Corp",
            email="contact@acme.com"
        )

        url = reverse("client-detail", args=[client.id])
        response = self.api_client.get(url)

        assert response.status_code == 200
        assert response.data["id"] == client.id
        assert response.data["name"] == "Acme Corp"
        assert response.data["email"] == "contact@acme.com"

    def test_retrieve_client_not_found(self):
        """
        GET /api/clients/{id}/ → 404
        """
        url = reverse("client-detail", args=[999])
        response = self.api_client.get(url)

        assert response.status_code == 404

    def test_create_client(self):
        """
        POST /api/clients/{id}/
        """
        url = reverse('client-list')
        data = {
            'name': "Jairo",
            'email': "jairo@hotmail.com"
        }
        response = self.api_client.post(url, data)

        assert response.status_code == 201