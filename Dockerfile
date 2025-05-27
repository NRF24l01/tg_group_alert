# Используем Python образ
FROM python:3.11-slim

# Set environment variables to prevent .pyc files and enable unbuffered output
ENV PYTHONDONTWRITEBYTECODE=1
ENV PYTHONUNBUFFERED=1

# Устанавливаем зависимости системы
# RUN apt-get update && apt-get install -y --no-install-recommends \
#     gcc libpq-dev \
#     && apt-get clean \
#     && rm -rf /var/lib/apt/lists/*

# Устанавливаем рабочую директорию
WORKDIR /app

# Копируем файлы проекта
COPY . .

# Install Python dependencies first for better caching
COPY requirements.txt .
RUN pip install --no-cache-dir -r requirements.txt

CMD ["bash", "start.sh"]
