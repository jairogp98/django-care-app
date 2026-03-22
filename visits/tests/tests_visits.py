import pytest


class TestVisitService:

    @pytest.mark.django_db()
    def test_create_visit(self, visit_factory):
        visit = visit_factory(summary="Esto es un summary")

        assert visit.status == "scheduled"
