# Backend-приложение для автоматизации закупок

Проект на Django/DRF с очередями фоновых задач на Celery и брокером Redis. Предназначен для автоматизации процессов закупок: управление пользователями, заказами и сопутствующей логикой через REST API.

## Стек
- Django 5 + Django REST Framework
- Celery 5 (фоновая обработка задач)
- Redis (брокер и backend результатов для Celery)
- Docker + docker-compose (опционально для контейнеризации)
- SQLite (по умолчанию; можно заменить на Postgres/MySQL)

## Архитектура и ключевые компоненты
- `orders/` — проект Django (настройки, wsgi, celery конфигурация).
- `backend/` — основное приложение (модели, API, бизнес-логика, кастомная модель пользователя `AUTH_USER_MODEL=backend.User`).
- Celery интегрирован через `orders/celery.py`, настройки берутся из Django `settings.py` с префиксом `CELERY_`.

## Требования
- Python 3.11+
- pip, venv
- Опционально: Redis (для запуска Celery локально без Docker)
- Либо Docker 24+ и docker-compose

## Переменные окружения
Опционально переопределяются (иначе берутся значения по умолчанию из `settings.py`):
- `DJANGO_SETTINGS_MODULE=orders.settings`
- `CELERY_BROKER_URL` — по умолчанию `redis://localhost:6379/0` (в docker-compose: `redis://redis:6379/0`)
- `CELERY_RESULT_BACKEND` — по умолчанию `redis://localhost:6379/1`

Почта (SMTP) указана в настройках как пример и должна быть заменена на реальные значения для продакшена.

## Локальный запуск (без Docker)
1) Клонировать репозиторий и перейти в каталог проекта.
2) Создать и активировать виртуальное окружение:
```bash
python3.11 -m venv .venv
source .venv/bin/activate
```
3) Установить зависимости:
```bash
pip install --upgrade pip
pip install -r requirements.txt
```
4) Применить миграции и запустить сервер разработки:
```bash
python manage.py migrate
python manage.py runserver 0.0.0.0:8000
```
Приложение будет доступно по адресу: http://localhost:8000

5) (Опционально) Запустить Celery worker для фоновых задач:
- Убедитесь, что Redis запущен локально (порт 6379) или укажите переменные `CELERY_BROKER_URL` и `CELERY_RESULT_BACKEND`.
```bash
CELERY_BROKER_URL=redis://localhost:6379/0 \
CELERY_RESULT_BACKEND=redis://localhost:6379/1 \
celery -A orders worker -l info
```

## Запуск в Docker
Полностью готов compose-стек: веб-приложение, Celery worker и Redis.

1) Собрать и запустить:
```bash
docker compose up --build
```
Это:
- применит миграции и поднимет Django на http://localhost:8000
- запустит Celery worker
- поднимет Redis на 6379

Остановить:
```bash
docker compose down
```

## Полезные команды
- Создание суперпользователя:
```bash
python manage.py createsuperuser
```
- Просмотр доступных команд:
```bash
python manage.py help
```
- Применение миграций:
```bash
python manage.py makemigrations
python manage.py migrate
```

## Аутентификация и доступ к API
- DRF включен. По умолчанию активны `TokenAuthentication` и `SessionAuthentication`.
- Базовый URL API — http://localhost:8000/
- Для доступа по токену отправляйте заголовок:
```
Authorization: Token <ваш_токен>
```
Токен можно выдать через админку либо выделенную конечную точку.

## Примечания по продакшену
- Установить `DEBUG=False` и корректно задать `ALLOWED_HOSTS`.
- Вынести секреты и SMTP-настройки в переменные окружения/секреты.
- Использовать внешнюю СУБД (PostgreSQL) и настроить резервное копирование.
- Настроить процесс-сервер (gunicorn/uvicorn) и обратный прокси (nginx) при деплое.

## Структура репозитория (сокращенно)
- `manage.py` — точка входа Django.
- `orders/settings.py` — настройки проекта.
- `orders/celery.py` — конфигурация Celery.
- `docker-compose.yml` — стек web + celery + redis.
- `Dockerfile` — образ приложения.
- `requirements.txt` — зависимости Python.

