import os
import logging

BOT_TOKEN = os.getenv('BOT_TOKEN')

if not BOT_TOKEN:
    logging.error("BOT_TOKEN не найден в переменных окружения!")
    logging.info("Установите переменную окружения:")
    logging.info("Linux/Mac: export BOT_TOKEN=your_token_here")
    logging.info("Windows: set BOT_TOKEN=your_token_here")
    logging.info("Или создайте файл .env с содержимым: BOT_TOKEN=your_token_here")
    raise ValueError("BOT_TOKEN не найден!")