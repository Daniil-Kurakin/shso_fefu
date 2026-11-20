# Инструкция по запуску сайта на штабсо-двфу.рф

Домен: `штабсо-двфу.рф`  
Punycode (техническое имя): `xn----7sbdfj2duafqj9a.xn--p1ai`

---

## Шаг 1. Настройка DNS у регистратора домена

В панели управления регистратора (где куплен домен `штабсо-двфу.рф` — Reg.ru, Beget, Webnames и т.д.):

1. Перейдите в раздел **Управление DNS-зоной** (или «Ресурсные записи»).
2. Добавьте две `A`-записи, указывающие на IP-адрес вашего сервера:
   * **Запись 1:**
     * Имя/Хост: `@` (или оставить пустым, если так требует регистратор)
     * Тип: `A`
     * Значение: `IP_АДРЕС_ВАШЕГО_СЕРВЕРА`
   * **Запись 2:**
     * Имя/Хост: `www`
     * Тип: `A`
     * Значение: `IP_АДРЕС_ВАШЕГО_СЕРВЕРА`
3. Сохраните изменения. Обновление DNS занимает от 15 минут до нескольких часов.

---

## Шаг 2. Подготовка сервера (VPS)

Рекомендуемый сервер: Ubuntu 22.04 / 24.04 LTS (2 vCPU, 2-4 GB RAM, 20-30 GB SSD в РФ — TimeWeb, Selectel, Beget и т.д.).

1. Подключитесь к серверу по SSH:
   ```bash
   ssh root@IP_АДРЕС_ВАШЕГО_СЕРВЕРА
   ```

2. Обновите пакеты:
   ```bash
   apt update && apt upgrade -y
   apt install -y git curl
   ```

---

## Шаг 3. Клонирование и настройка проекта

1. Склонируйте репозиторий на сервер:
   ```bash
   git clone <URL_ВАШЕГО_РЕПОЗИТОРИЯ> /opt/shso_fefu
   cd /opt/shso_fefu
   ```

2. Создайте боевой конфигурационный файл `.env`:
   ```bash
   cp .env.prod.example .env
   nano .env
   ```
   В файле `.env`:
   - Сгенерируйте и вставьте надежный `DJANGO_SECRET_KEY`:
     ```bash
     python3 -c "import secrets; print(secrets.token_urlsafe(50))"
     ```
   - Задайте надежный пароль для базы данных в `POSTGRES_PASSWORD`.
   - Впишите боевой токен Telegram-бота (`TELEGRAM_BOT_TOKEN`) и chat ID штаба (`TELEGRAM_HQ_CHAT_ID`).
   - Настройте доступ к почтовому серверу (SMTP).

---

## Шаг 4. Запуск (деплой)

Запустите подготовленный скрипт деплоя:
```bash
bash scripts/deploy.sh
```

Скрипт автоматически:
1. Проверит и установит Docker и Docker Compose (если еще не установлены).
2. Соберет production-образы с Gunicorn, Postgres, Redis, Celery/Django-Q и Caddy.
3. Применит все миграции базы данных (`migrate`).
4. Соберет статически файлы с компрессией WhiteNoise (`collectstatic`).
5. Caddy автоматически запросит и выпустит бесплатный SSL-сертификат Let's Encrypt для `xn----7sbdfj2duafqj9a.xn--p1ai` и настроит редирект с `http://` на `https://`.

---

## Шаг 5. Создание учетной записи администратора

Создайте суперпользователя штаба:
```bash
docker compose -f docker-compose.prod.yml exec web python manage.py createsuperuser
```

После этого административная панель будет доступна по адресу:
`https://штабсо-двфу.рф/admin/`

---

## Шаг 6. Настройка резервного копирования (Cron)

Настройте ежедневный автоматический бэкап базы данных и медиа-файлов в 03:00 ночи:

1. Откройте crontab:
   ```bash
   crontab -e
   ```
2. Добавьте строку:
   ```cron
   0 3 * * * /bin/bash /opt/shso_fefu/scripts/backup.sh >> /var/log/shso_backup.log 2>&1
   ```
3. Бэкапы сохраняются в папку `/opt/shso_fefu/backups/` и хранятся 14 дней.

---

## Полезные команды управления на сервере

```bash
# Просмотр статуса контейнеров
docker compose -f docker-compose.prod.yml ps

# Просмотр логов (в реальном времени)
docker compose -f docker-compose.prod.yml logs -f web
docker compose -f docker-compose.prod.yml logs -f caddy

# Перезапуск сервисов
docker compose -f docker-compose.prod.yml restart

# Обновление кода после git pull
git pull
bash scripts/deploy.sh
```
