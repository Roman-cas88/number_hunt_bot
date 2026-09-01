import asyncio
import logging
from aiogram import Bot, Dispatcher
from config import BOT_TOKEN
from handlers import common_router, admin_router, game_router
from database import Database

logging.basicConfig(level=logging.INFO)

bot = Bot(token=BOT_TOKEN)
dp = Dispatcher()

# Подключаем роутеры
dp.include_router(common_router)
dp.include_router(admin_router)
dp.include_router(game_router)

async def main():
    # Инициализация БД (создаст таблицы)
    db = Database()
    # Запуск поллинга
    await dp.start_polling(bot)

if __name__ == "__main__":
    asyncio.run(main())