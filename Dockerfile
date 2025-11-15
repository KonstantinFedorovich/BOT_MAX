FROM python:3.11-slim

WORKDIR /app

# Копируем зависимости first для кэширования слоев
COPY requirements.txt .

# Устанавливаем Python зависимости
RUN pip install --no-cache-dir -r requirements.txt

# Копируем только нужные исходные файлы
COPY main.py config.py .env ./

# Создаем папку для данных (если нужно)
RUN mkdir -p /data

# Запускаем бота
CMD ["python", "main.py"]