from datetime import timedelta
from io import StringIO

import pytest
from django.core.management import call_command
from django.utils import timezone

from apps.accounts.models import User
from apps.requests.models import PassRequest, PassVisitor

pytestmark = pytest.mark.django_db


def test_purge_expired_passes_command():
    user = User.objects.create_user("test_purge@example.com", "pass-123")
    today = timezone.localdate()

    # Заявка, срок которой истёк (мероприятие было больше 30 дней назад)
    expired_pass = PassRequest.objects.create(
        user=user,
        title="Старое мероприятие",
        visit_date=today - timedelta(days=40),
    )
    visitor1 = PassVisitor.objects.create(
        request=expired_pass,
        full_name="Архивный Гость",
        document_data="0515 000111",
        phone="+79991112233",
    )

    # Свежая заявка (мероприятие только что прошло)
    fresh_pass = PassRequest.objects.create(
        user=user,
        title="Свежее мероприятие",
        visit_date=today - timedelta(days=5),
    )
    visitor2 = PassVisitor.objects.create(
        request=fresh_pass,
        full_name="Свежий Гость",
        document_data="0515 777888",
        phone="+79995556677",
    )

    out = StringIO()
    call_command("purge_expired_passes", stdout=out)

    output = out.getvalue()
    assert "Успешно очищены" in output

    expired_pass.refresh_from_db()
    visitor1.refresh_from_db()
    assert expired_pass.is_data_purged is True
    assert "152-ФЗ" in visitor1.document_data
    assert visitor1.phone == ""

    fresh_pass.refresh_from_db()
    visitor2.refresh_from_db()
    assert fresh_pass.is_data_purged is False
    assert visitor2.document_data == "0515 777888"
