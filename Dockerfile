# Используем Python образ
FROM python:3.11-slim

# Устанавливаем зависимости системы
RUN apt-get update && apt-get install -y \
    libpq-dev gcc \
    && rm -rf /var/lib/apt/lists/*

# Копируем файлы проекта
COPY . /app

# Устанавливаем рабочую директорию
WORKDIR /app

# Устанавливаем зависимости из requirements.txt
RUN pip install --no-cache-dir -r requirements.txt

# Выполняем миграции alembic
RUN alembic upgrade head

# Команда запуска бота
CMD ["python", "bot.py"]
