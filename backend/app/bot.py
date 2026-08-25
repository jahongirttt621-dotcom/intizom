"""Telegram bot: /start buyrug'i Mini App'ni ochadigan tugma yuboradi."""

import logging

from aiogram import Bot, Dispatcher, F
from aiogram.filters import Command
from aiogram.types import (
    InlineKeyboardButton,
    InlineKeyboardMarkup,
    KeyboardButton,
    Message,
    ReplyKeyboardMarkup,
    WebAppInfo,
)

from app.config import settings

logger = logging.getLogger(__name__)

bot = Bot(token=settings.BOT_TOKEN)
dp = Dispatcher()


def _main_keyboard() -> InlineKeyboardMarkup:
    return InlineKeyboardMarkup(
        inline_keyboard=[
            [InlineKeyboardButton(text="🚀 Ilovani ochish", web_app=WebAppInfo(url=settings.WEBAPP_URL))]
        ]
    )


def _reply_keyboard() -> ReplyKeyboardMarkup:
    # pastdagi doimiy tugma
    return ReplyKeyboardMarkup(
        keyboard=[[KeyboardButton(text="📊 Intizom", web_app=WebAppInfo(url=settings.WEBAPP_URL))]],
        resize_keyboard=True,
    )


@dp.message(Command("start"))
async def cmd_start(message: Message) -> None:
    text = (
        f"Salom, {message.from_user.first_name}! 👋\n\n"
        "Bu <b>Intizom</b> — ommaviy odat challenge platformasi.\n\n"
        "• Challenge tanla\n"
        "• Har kuni bajarganingni belgila\n"
        "• Streak yig'\n"
        "• Reytingda ko'tarilib boshqalar bilan raqobatlash\n\n"
        "Boshlash uchun ilovani och 👇"
    )
    await message.answer(text, parse_mode="HTML", reply_markup=_main_keyboard())
    await message.answer("Tez kirish uchun:", reply_markup=_reply_keyboard())


@dp.message(Command("myid"))
async def cmd_myid(message: Message) -> None:
    """Foydalanuvchi o'z Telegram ID'sini bilib oladi (admin sozlash uchun)."""
    await message.answer(
        f"Sizning Telegram ID: <code>{message.from_user.id}</code>\n\n"
        "Admin bo'lish uchun shu raqamni serverdagi ADMIN_ID ga qo'ying.",
        parse_mode="HTML",
    )


@dp.message(Command("help"))
async def cmd_help(message: Message) -> None:
    await message.answer(
        "Ilovani ochib challenge tanlang va har kuni check-in qiling.\n"
        "Streak uzilmasligi uchun kunni o'tkazib yubormang!",
        reply_markup=_main_keyboard(),
    )


@dp.message(F.web_app_data)
async def on_webapp_data(message: Message) -> None:
    """Mini App'dan tg.sendData() orqali kelgan ma'lumot (ixtiyoriy)."""
    await message.answer(f"Qabul qilindi: {message.web_app_data.data}")


async def run_bot() -> None:
    logger.info("Bot polling boshlandi")
    await dp.start_polling(bot)
