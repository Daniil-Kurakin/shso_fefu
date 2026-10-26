import pytest

from apps.squads.models import Direction, Squad

pytestmark = pytest.mark.django_db


def test_direction_creation():
    direction = Direction.objects.create(name="Педагогическое", icon="🎓")
    assert direction.slug == "педагогическое"
    assert str(direction) == "Педагогическое"


def test_squad_creation():
    direction = Direction.objects.create(name="Строительное", icon="🏗️")
    squad = Squad.objects.create(
        name="ССО «Приморец»",
        direction=direction,
        founding_year=2015,
        is_recruiting=True,
    )
    assert squad.direction == direction
    assert squad.is_recruiting is True
    assert str(squad) == "ССО «Приморец»"
    assert squad.slug  # auto-generated
