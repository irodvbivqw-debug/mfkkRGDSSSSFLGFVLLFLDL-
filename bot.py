import os
import sys
import logging
import asyncio

from aiogram import Bot, Dispatcher
from aiogram.types import Message
from aiogram.filters import Command

logging.basicConfig(level=logging.INFO)
logger = logging.getLogger(__name__)

NEEDED_VARS = [
    "BOT_TOKEN",
    "OPERATORS_GROUP_ID",
    "CHANNEL_ID",
    "CHANNEL_INVITE_LINK",
    "SUPPORT_USERNAME",
    "ADMIN_IDS",
    "BOT_LINK",
    "ENV",
]


def log_env_presence():
    for k in NEEDED_VARS:
        logger.info(f"{k} present: {bool(os.environ.get(k))}")


async def run_bot():
    BOT_TOKEN = os.environ.get("BOT_TOKEN")
    if not BOT_TOKEN:
        logger.error("Missing BOT_TOKEN environment variable. Set it in Railway Variables.")
        # Exit with non‑zero to make the failure obvious in logs
        sys.exit(1)

    bot = Bot(token=BOT_TOKEN)
    dp = Dispatcher()

    @dp.message(Command("start"))
    async def cmd_start(message: Message):
        await message.answer("Привет! Бот запущен.")

    try:
        logger.info("Starting polling")
        await dp.start_polling(bot)
    finally:
        await bot.session.close()


def main():
    # Логируем, какие переменные видны (без вывода секретов)
    log_env_presence()
    # Запускаем бота
    asyncio.run(run_bot())


if __name__ == "__main__":
    main()
