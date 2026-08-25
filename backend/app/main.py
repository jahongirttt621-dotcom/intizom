"""
Kirish nuqtasi.

Bitta process ichida uchtasini birga ishga tushiradi:
1. FastAPI API server (mini app frontend uchun)
2. Telegram bot (polling)
3. Scheduler (har kuni uzilgan streak'larni tozalash)

Ishga tushirish:  python -m app.main
"""

import asyncio
import contextlib
import logging

from apscheduler.schedulers.asyncio import AsyncIOScheduler
from apscheduler.triggers.cron import CronTrigger
from fastapi import FastAPI
from fastapi.middleware.cors import CORSMiddleware
import uvicorn

from app.bot import run_bot
from app.config import settings
from app.database import SessionLocal, init_db
from app.routers.api import router as api_router
from app.services import reset_broken_streaks, seed_default_challenges

logging.basicConfig(level=logging.INFO, format="%(asctime)s [%(levelname)s] %(name)s: %(message)s")
logger = logging.getLogger("intizom")

app = FastAPI(title="Intizom API")

# CORS — mini app boshqa domendan (GitHub Pages) so'rov yuboradi
app.add_middleware(
    CORSMiddleware,
    allow_origins=["*"],  # productionda WEBAPP_URL bilan cheklang
    allow_methods=["*"],
    allow_headers=["*"],
)
app.include_router(api_router)


@app.get("/health")
async def health():
    return {"status": "ok"}


async def _daily_streak_job() -> None:
    async with SessionLocal() as session:
        n = await reset_broken_streaks(session)
        logger.info("Streak tozalash: %d ta uzildi", n)


async def _startup_data() -> None:
    await init_db()
    async with SessionLocal() as session:
        await seed_default_challenges(session)
    logger.info("DB tayyor")


async def main() -> None:
    await _startup_data()

    # Scheduler — har kuni 00:05 da uzilgan streak'larni tozalaydi
    scheduler = AsyncIOScheduler(timezone=settings.TIMEZONE)
    scheduler.add_job(_daily_streak_job, CronTrigger(hour=0, minute=5))
    scheduler.start()

    # Uvicorn server'ni dastur ichida ishga tushiramiz
    config = uvicorn.Config(app, host=settings.API_HOST, port=settings.API_PORT, log_level="info")
    server = uvicorn.Server(config)

    # bot va API'ni birga yuritamiz
    await asyncio.gather(server.serve(), run_bot())


if __name__ == "__main__":
    with contextlib.suppress(KeyboardInterrupt):
        asyncio.run(main())
