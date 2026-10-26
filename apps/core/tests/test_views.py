import pytest

pytestmark = pytest.mark.django_db


def test_healthz_ok(client):
    response = client.get("/healthz")
    assert response.status_code == 200
    assert response.json() == {"status": "ok"}


def test_root_redirects_to_language_prefix(client):
    response = client.get("/")
    assert response.status_code == 302
    assert response["Location"] in {"/ru/", "/en/"}


@pytest.mark.parametrize("lang", ["ru", "en"])
def test_home_available_in_both_languages(client, lang):
    response = client.get(f"/{lang}/")
    assert response.status_code == 200
    assert f'lang="{lang}"'.encode() in response.content
