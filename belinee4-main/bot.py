import os
import sys
import logging
from aiogram import Bot, Dispatcher, types
from aiogram.utils import executor

logging.basicConfig(level=logging.INFO)
logger = logging.getLogger(__name__)

# Load local .env only in development mode
if os.getenv("ENV", "production") == "development":
    try:
        from dotenv import load_dotenv
        load_dotenv()
        logger.info("Loaded .env for development")
    except Exception:
        logger.info("python-dotenv not installed or .env not found")

BOT_TOKEN = os.environ.get("BOT_TOKEN")

if not BOT_TOKEN:
    logger.error("Missing BOT_TOKEN environment variable. Set it in Railway Variables or .env (for local dev).")
    sys.exit(1)

bot = Bot(token=BOT_TOKEN)
dp = Dispatcher(bot)

@dp.message("/start")
async def cmd_start(message: types.Message):
    await message.reply("Привет! Бот запущен.")


def main():
    # Long polling. If you use webhooks, configure separately.
    executor.start_polling(dp, skip_updates=True)


if __name__ == "__main__":
    main()
