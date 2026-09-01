import os
from dotenv import load_dotenv

load_dotenv()

BOT_TOKEN = os.getenv("BOT_TOKEN")
ADMIN_IDS = list(map(int, os.getenv("ADMIN_IDS", "").split(",")))  # например, "123456789,987654321"

# Путь к базе данных
DB_PATH = "/tmp/game.db"

# Настройки напоминаний
REMINDER_INTERVAL_SECONDS = 3600  # 1 час
REMINDER_START_AFTER_SECONDS = 3600  # через час после начала голосования