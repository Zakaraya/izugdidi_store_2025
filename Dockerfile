# Dockerfile
FROM python:3.12-slim

ENV PYTHONDONTWRITEBYTECODE=1 \
    PYTHONUNBUFFERED=1

# Системные пакеты: компилятор, libpq для Postgres, gettext для i18n, build deps для Pillow
RUN apt-get update && apt-get install -y --no-install-recommends \
    build-essential \
    libpq-dev \
    gettext \
    libjpeg62-turbo-dev zlib1g-dev \
    curl ca-certificates \
    && rm -rf /var/lib/apt/lists/*

# Создадим пользователя без привилегий
RUN useradd -m appuser
WORKDIR /app

# Установка Python-зависимостей
COPY requirements.txt /app/requirements.txt
RUN pip install --no-cache-dir -r /app/requirements.txt

# Папка проекта и права
COPY --chown=appuser:appuser . /app
RUN mkdir -p /app/data && chown -R appuser:appuser /app
USER appuser

# По умолчанию держим контейнер живым до настройки проекта (далее поменяем команду)
CMD ["tail", "-f", "/dev/null"]
