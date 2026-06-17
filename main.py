from os import getenv
import asyncio
from aiogram import Bot, Dispatcher
from dotenv import load_dotenv
from revenge import router, notifier

load_dotenv()
TOKEN = getenv("BOT_TOKEN")

dp = Dispatcher()
dp.include_router(router)

async def main():
    bot = Bot(token = TOKEN)

    asyncio.create_task(notifier(bot))

    await dp.start_polling(bot)

if __name__ == '__main__':
    asyncio.run(main())