# shso_fefu — сайт Штаба студенческих отрядов ДВФУ

Python 3.12 · Django 5.2 LTS · PostgreSQL 16 · Redis · Django-Q2 · HTMX/Alpine.js/Tailwind (подключаются в части 2).
Документы проекта: ТЗ v1.0 и план работ (в корне не хранятся, лежат у заказчика).

## Что нужно на Windows

1. **WSL2** (откройте PowerShell от администратора: `wsl --install`, затем перезагрузка).
2. **Docker Desktop** (включите «Use the WSL 2 based engine»).
3. **Git for Windows** и **VS Code** (расширения предложит поставить сам VS Code из `.vscode/extensions.json`).

Python и Node на Windows ставить не нужно: всё работает в контейнерах.

> Совет: клонируйте репозиторий в файловую систему WSL (например `\\wsl$\Ubuntu\home\<вы>\shso_fefu`) — контейнеры работают заметно быстрее, чем на диске `C:`. На `C:` тоже заработает.

## Первый запуск

```powershell
git clone https://github.com/Daniil-Kurakin/shso_fefu.git
cd shso_fefu
copy .env.example .env
docker compose build
docker compose run --rm web uv lock                              # создаст uv.lock, закоммитьте его
docker compose run --rm web python manage.py makemigrations accounts   # первая миграция, закоммитьте её
docker compose up
```

Сайт: http://localhost:8000 (перенаправит на `/ru/`), проверка живости: http://localhost:8000/healthz

Создать владельца (суперпользователя):

```powershell
docker compose exec web python manage.py createsuperuser
```

Админ-панель: http://localhost:8000/ru/admin/

## Ежедневные команды

| Что | Команда |
| --- | --- |
| Запустить | `docker compose up` |
| Остановить | `docker compose down` (данные БД сохраняются; `down -v` удалит и их) |
| Тесты | `docker compose run --rm web pytest` |
| Линтер | `docker compose run --rm web ruff check .` |
| Автоформат | `docker compose run --rm web ruff format .` |
| Новая миграция | `docker compose run --rm web python manage.py makemigrations` |
| Строки для перевода | `docker compose run --rm web python manage.py makemessages -l en` |
| Оболочка Django | `docker compose exec web python manage.py shell` |

`pre-commit` (проверки при каждом коммите) удобнее поставить один раз локально: `pip install pre-commit` и `pre-commit install`. Это необязательно, CI проверяет то же самое.

## Структура

```
config/            настройки (base / dev / test / prod), urls, wsgi/asgi
apps/core          главная, healthz, общие компоненты
apps/accounts      пользователи и системные роли
apps/squads        отряды, членство, переходы        (заготовка)
apps/news          новости                            (заготовка)
apps/vacancies     вакансии и отклики                 (заготовка)
apps/requests      заявки на помещения и пропуска     (заготовка)
apps/content       цитаты, контакты, настройки сайта  (заготовка)
templates/         общие шаблоны
static/            статика проекта
```

## Правила работы

- Ветка `main` защищена, работа идёт в ветках `feature/…`, `fix/…`, слияние через Pull Request после зелёного CI и ревью.
- Коммиты в стиле Conventional Commits: `feat: …`, `fix: …`, `docs: …`, `chore: …`, `test: …`.
- Любое изменение моделей сопровождается миграцией. Права доступа и процессы согласования не сливаются без автотестов.
- Реальные персональные данные в разработке не используются.
- Секреты только в `.env` (он в `.gitignore`) или переменных окружения сервера.

Рекомендуемые настройки GitHub: Settings → Branches → защитить `main` (требовать PR и прохождение проверок `lint` и `test`).
