from rest_framework import serializers
from clients.models.models import Client
from visits.serializers.serializers import VisitListSerializer


class ClientSerializer(serializers.ModelSerializer):
    class Meta:
        model = Client
        fields = ("id", "name", "email")

    def validate_email(self, value):
        value = value.strip().lower()

        if not '@' in value:
            raise serializers.ValidationError("Formato del email erroneo")

        return value

class ClientVisitSerializer(serializers.ModelSerializer):
    visits = VisitListSerializer(many=True, read_only=True)
    total_visits = serializers.IntegerField(read_only=True)

    class Meta:
        model = Client
        fields = ("id",
                  "name",
                  "email",
                  "visits",
                  "total_visits")



