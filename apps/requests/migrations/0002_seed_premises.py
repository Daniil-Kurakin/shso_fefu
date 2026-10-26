from django.db import migrations


def seed_premises(apps, schema_editor):
    CampusPremise = apps.get_model("requests", "CampusPremise")
    premises = [
        {
            "name": "Аудитория А826 (Штаб ШСО ДВФУ)",
            "building": "A",
            "floor": 8,
            "room_number": "А826",
            "capacity": 35,
            "equipment_description": "Проектор, экран, акустическая система, круглый стол, флипчарт",
            "is_active": True,
            "order": 1,
        },
        {
            "name": "«Синий зал»",
            "building": "A",
            "floor": 3,
            "room_number": "А302",
            "capacity": 150,
            "equipment_description": "Большой проектор, радиомикрофоны, трибуна, звукорежиссёрский пульт",
            "is_active": True,
            "order": 2,
        },
        {
            "name": "Коворкинг «Аякс»",
            "building": "B",
            "floor": 4,
            "room_number": "В401",
            "capacity": 80,
            "equipment_description": "Мобильные столы, пуфы, проектор, маркерная стена",
            "is_active": True,
            "order": 3,
        },
        {
            "name": "Аудитория С501 (Репетиции и сборы)",
            "building": "C",
            "floor": 5,
            "room_number": "С501",
            "capacity": 45,
            "equipment_description": "Парты, доска, мультимедиа-панель",
            "is_active": True,
            "order": 4,
        },
        {
            "name": "Аудитория Е310 (Спевки и лекции)",
            "building": "E",
            "floor": 3,
            "room_number": "Е310",
            "capacity": 60,
            "equipment_description": "Проектор, усилитель звука, фортепиано",
            "is_active": True,
            "order": 5,
        },
    ]
    for p in premises:
        CampusPremise.objects.get_or_create(name=p["name"], defaults=p)


def unseed_premises(apps, schema_editor):
    CampusPremise = apps.get_model("requests", "CampusPremise")
    CampusPremise.objects.filter(
        name__in=[
            "Аудитория А826 (Штаб ШСО ДВФУ)",
            "«Синий зал»",
            "Коворкинг «Аякс»",
            "Аудитория С501 (Репетиции и сборы)",
            "Аудитория Е310 (Спевки и лекции)",
        ]
    ).delete()


class Migration(migrations.Migration):
    dependencies = [
        ("requests", "0001_initial"),
    ]

    operations = [
        migrations.RunPython(seed_premises, unseed_premises),
    ]
