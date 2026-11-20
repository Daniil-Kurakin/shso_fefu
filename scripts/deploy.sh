#!/usr/bin/env bash
set -euo pipefail

# =====================================================================
# Скрипт развертывания ШСО ДВФУ (штабсо-двфу.рф)
# Использование: bash scripts/deploy.sh
# =====================================================================

PROJECT_DIR="$(cd "$(dirname "${BASH_SOURCE[0]}")/.." && pwd)"
cd "$PROJECT_DIR"

echo "==> [1/5] Проверка окружения..."
if [ ! -f .env ]; then
    echo "ОШИБКА: Файл .env не найден!"
    echo "Скопируйте .env.prod.example в .env и заполните боевые переменные:"
    echo "  cp .env.prod.example .env"
    echo "  nano .env"
    exit 1
fi

# Проверка наличия Docker
if ! command -v docker &> /dev/null; then
    echo "Docker не установлен. Установка Docker..."
    curl -fsSL https://get.docker.com | sh
    sudo usermod -aG docker "$USER" || true
    echo "Docker успешно установлен."
fi

echo "==> [2/5] Сборка и запуск контейнеров..."
docker compose -f docker-compose.prod.yml build
docker compose -f docker-compose.prod.yml up -d --remove-orphans

echo "==> [3/5] Ожидание готовности сервисов..."
sleep 5

echo "==> [4/5] Проверка статуса..."
docker compose -f docker-compose.prod.yml ps

echo "==> [5/5] Проверка работоспособности приложения..."
for i in {1..30}; do
    if docker compose -f docker-compose.prod.yml exec -T web python -c "import urllib.request; urllib.request.urlopen('http://127.0.0.1:8000/healthz')" &>/dev/null; then
        echo "Приложение успешно запущено и отвечает 200 OK на /healthz!"
        break
    fi
    echo "Ожидание старта Django ($i/30)..."
    sleep 2
done

echo ""
echo "=========================================================="
echo " Деплой завершен! Сайт доступен на:"
echo " https://штабсо-двфу.рф (https://xn----7sbdfj2duafqj9a.xn--p1ai)"
echo ""
echo " Для создания суперпользователя выполните:"
echo " docker compose -f docker-compose.prod.yml exec web python manage.py createsuperuser"
echo "=========================================================="
