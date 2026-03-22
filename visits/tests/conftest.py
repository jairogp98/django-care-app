from datetime import timedelta

import pytest
from django.contrib.auth import get_user_model
from django.utils import timezone

from clients.models.models import Client
from visits.models.models import Visit


@pytest.fixture
def client():
    return Client.objects.create(
        name="Test client",
        email="test@test.com",
    )

@pytest.fixture
def caregiver():
    User = get_user_model()
    return User.objects.create_user(
        username="caregiver_test",
        password="testpass123",
        email="caregiver@test.com",
    )

@pytest.fixture
def visit_factory(client, caregiver):
    def create_visit(**kwargs):
        data = {
            "client": client,
            "assigned_caregiver": caregiver,
            "visit_type": "physiotherapy",
            "scheduled_start": timezone.now() + timedelta(days=1, hours=7),
            "scheduled_end": timezone.now() + timedelta(days=1, hours=8)
        }
        data.update(kwargs)
        return Visit.objects.create(**data)

    return create_visit
