from rest_framework import serializers
from clients.models.models import Client


class ClientSerializer(serializers.ModelSerializer):
    class Meta:
        model = Client
        fields = ("id", "name", "email")

    def validate_email(self, value):
        value = value.strip().lower()

        if not '@' in value:
            raise serializers.ValidationError("Formato del email erroneo")

        return value



