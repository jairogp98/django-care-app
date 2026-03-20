from clients.models.models import Client

class ClientNotFound(Exception):
    pass

class ClientService:

    @staticmethod
    def create_client(data) -> Client:
        client = Client.objects.create(
            name=data.get("name"),
            email=data.get("email")
        )
        return client