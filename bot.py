import asyncio
import logging
import os
import re
import tempfile
from pathlib import Path
from urllib.parse import urlparse

from aiogram import Bot, Dispatcher, F
from aiogram.filters import CommandStart
from aiogram.types import FSInputFile, Message
from yt_dlp import YoutubeDL

logging.basicConfig(level=logging.INFO)

# Token muhit o'zgaruvchisidan olinadi (kodga yozilmaydi!)
TOKEN = os.getenv("BOT_TOKEN")
if not TOKEN:
    raise SystemExit("BOT_TOKEN topilmadi. Avval tokenni sozlang.")

# Hozircha faqat TikTok. Keyingi bosqichda YouTube va Instagram qo'shiladi.
ALLOWED_DOMAINS = {"tiktok.com"}

# Oddiy Telegram Bot API orqali yuboriladigan fayl chegarasi (MB)
MAX_SIZE_MB = 50

bot = Bot(TOKEN)
dp = Dispatcher()

URL_RE = re.compile(r"https?://\S+")


def is_allowed(url):
    host = (urlparse(url).hostname or "").lower()
    return any(host == d or host.endswith("." + d) for d in ALLOWED_DOMAINS)


def download_video(url, folder):
    """Videoni yuklab oladi va fayl yo'lini qaytaradi (bo'lmasa None)."""
    opts = {
        "outtmpl": os.path.join(folder, "%(id)s.%(ext)s"),
        "format": "best[ext=mp4]/best",
        "noplaylist": True,
        "quiet": True,
        "no_warnings": True,
        "max_filesize": MAX_SIZE_MB * 1024 * 1024,
    }
    with YoutubeDL(opts) as ydl:
        info = ydl.extract_info(url, download=True)
        path = Path(ydl.prepare_filename(info))
    return path if path.exists() else None


@dp.message(CommandStart())
async def start(message: Message):
    await message.answer(
        "Salom! 👋 TikTok havolasini yuboring, men videoni yuklab beraman."
    )


@dp.message(F.text)
async def handle_link(message: Message):
    match = URL_RE.search(message.text)
    if not match:
        await message.answer("Iltimos, video havolasini yuboring.")
        return

    url = match.group(0)
    if not is_allowed(url):
        await message.answer("Hozircha faqat TikTok havolalari qo'llab-quvvatlanadi.")
        return

    status = await message.answer("Yuklab olinmoqda... ⏳")
    try:
        with tempfile.TemporaryDirectory() as folder:
            path = await asyncio.to_thread(download_video, url, folder)
            if path is None or path.stat().st_size > MAX_SIZE_MB * 1024 * 1024:
                await status.edit_text(
                    f"Videoni yuklab bo'lmadi yoki u {MAX_SIZE_MB} MB dan katta."
                )
                return
            await message.answer_video(FSInputFile(path))
        await status.delete()
    except Exception:
        logging.exception("Yuklashda xato")
        await status.edit_text(
            "Xatolik yuz berdi. Havolani tekshirib, qayta urinib ko'ring."
        )


async def main():
    logging.info("Bot ishga tushdi")
    await dp.start_polling(bot)


if __name__ == "__main__":
    asyncio.run(main())
