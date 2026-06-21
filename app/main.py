import asyncio
import os
from contextlib import asynccontextmanager

import uvicorn
from dotenv import load_dotenv
from fastapi import FastAPI
from fastapi.middleware.cors import CORSMiddleware
from slowapi import _rate_limit_exceeded_handler
from slowapi.errors import RateLimitExceeded
from aiogram import Bot, Dispatcher

from app.bot.handlers import router as bot_router
from app.api.routes import router as api_router
from app.limiter import limiter

load_dotenv()


@asynccontextmanager
async def lifespan(app: FastAPI):
    bot = Bot(token=os.getenv("TELEGRAM_BOT_TOKEN"))
    dp = Dispatcher()
    dp.include_router(bot_router)

    polling_task = asyncio.create_task(
        dp.start_polling(bot, handle_signals=False)
    )
    print("✅ Graphector bot started")
    yield
    polling_task.cancel()
    await bot.session.close()
    print("🛑 Graphector bot stopped")


app = FastAPI(
    title="Graphector",
    description="LangGraph multi-agent code review service",
    version="1.0.0",
    lifespan=lifespan,
)

# Rate limiter
app.state.limiter = limiter
app.add_exception_handler(RateLimitExceeded, _rate_limit_exceeded_handler)

# CORS (если будет фронтенд)
app.add_middleware(
    CORSMiddleware,
    allow_origins=["*"],
    allow_methods=["*"],
    allow_headers=["*"],
)

app.include_router(api_router)

if __name__ == "__main__":
    uvicorn.run("app.main:app", host="0.0.0.0", port=8010, reload=False)
