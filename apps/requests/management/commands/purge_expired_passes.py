from django.core.management.base import BaseCommand
from django.utils import timezone

from apps.requests.models import PassRequest


class Command(BaseCommand):
    help = "Автоматическая очистка персональных данных посетителей по истечении 30 дней (152-ФЗ)"

    def handle(self, *args, **options):
        today = timezone.localdate()
        expired_requests = PassRequest.objects.filter(
            data_deletion_scheduled_at__lte=today,
            is_data_purged=False,
        )
        count = 0
        for req in expired_requests:
            req.purge_personal_data()
            count += 1

        self.stdout.write(
            self.style.SUCCESS(
                f"Успешно очищены персональные данные для {count} заявок на пропуска."
            )
        )
