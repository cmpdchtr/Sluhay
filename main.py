import asyncio
import logging
import aiohttp
import os
from aiogram import Bot, Dispatcher, F
from aiogram.filters import Command
from aiogram.types import Message, FSInputFile, BufferedInputFile
from aiogram.enums import ParseMode

import config
from spotify_service import SpotifyService
from youtube_downloader import YouTubeDownloader


# Налаштування логування
logging.basicConfig(
    level=logging.INFO,
    format='%(asctime)s - %(name)s - %(levelname)s - %(message)s'
)
logger = logging.getLogger(__name__)

# Ініціалізація бота
bot = Bot(token=config.TELEGRAM_BOT_TOKEN)
dp = Dispatcher()

# Ініціалізація сервісів
spotify = SpotifyService()
youtube = YouTubeDownloader()


@dp.message(Command("start"))
async def cmd_start(message: Message):
    """Обробник команди /start"""
    welcome_text = (
        "👋 Привіт! Я <b>Sluhay</b> — бот для завантаження музики!\n\n"
        "🎵 <b>Як мною користуватись:</b>\n"
        "1. Надішли мені посилання на трек зі Spotify\n"
        "2. Або напиши назву пісні та виконавця\n\n"
        "📥 Я знайду трек і завантажу його для тебе!\n\n"
        "💡 <b>Приклади:</b>\n"
        "• https://open.spotify.com/track/...\n"
        "• МУР - Не побачу того дня\n"
        "• The Weeknd - Blinding Lights\n\n"
        "❓ Команди:\n"
        "/start - Почати роботу з ботом\n"
        "/help - Допомога"
    )
    await message.answer(welcome_text, parse_mode=ParseMode.HTML)


@dp.message(Command("help"))
async def cmd_help(message: Message):
    """Обробник команди /help"""
    help_text = (
        "ℹ️ <b>Довідка по боту Sluhay</b>\n\n"
        "🎵 <b>Способи завантаження:</b>\n\n"
        "<b>1. За посиланням Spotify:</b>\n"
        "Надішли мені посилання на трек, наприклад:\n"
        "<code>https://open.spotify.com/track/...</code>\n\n"
        "<b>2. За назвою:</b>\n"
        "Просто напиши назву пісні та виконавця:\n"
        "<code>Виконавець - Назва пісні</code>\n\n"
        "⏱ Завантаження зазвичай займає 10-30 секунд.\n\n"
        "⚠️ <b>Важливо:</b>\n"
        "• Якість аудіо: 192 kbps MP3\n"
        "• Максимальний розмір файлу: 50 МБ\n"
        "• Бот шукає трек на YouTube за даними зі Spotify\n\n"
        "❓ Питання чи проблеми? Напиши в тех. підтримку - @cmpdchtr!"
    )
    await message.answer(help_text, parse_mode=ParseMode.HTML)


@dp.message(F.text)
async def handle_message(message: Message):
    """Обробник текстових повідомлень"""
    user_input = message.text.strip()
    
    # Відправляємо повідомлення про обробку
    status_msg = await message.answer("🔍 Шукаю трек...")
    
    try:
        track_info = None
        
        # Перевіряємо, чи це посилання Spotify
        if "spotify.com" in user_input or "spotify:" in user_input:
            logger.info(f"Обробка Spotify URL: {user_input}")
            track_info = spotify.get_track_info(user_input)
            
            if not track_info:
                await status_msg.edit_text(
                    "❌ Не вдалося отримати інформацію про трек зі Spotify.\n"
                    "Перевір посилання і спробуй ще раз."
                )
                return
        else:
            # Пошук треку за текстовим запитом
            logger.info(f"Пошук треку: {user_input}")
            track_info = spotify.search_track(user_input)
            
            if not track_info:
                await status_msg.edit_text(
                    "❌ Трек не знайдено на Spotify.\n"
                    "Спробуй інший запит або надішли посилання."
                )
                return
        
        # Виводимо інформацію про знайдений трек
        info_text = (
            f"✅ Знайдено трек!\n\n"
            f"🎵 <b>{track_info['name']}</b>\n"
            f"👤 {track_info['artists']}\n"
            f"💿 Альбом: {track_info['album']}\n\n"
            f"⏳ Завантажую з YouTube..."
        )
        await status_msg.edit_text(info_text, parse_mode=ParseMode.HTML)
        
        # Завантажуємо аудіо з YouTube
        logger.info(f"Завантаження: {track_info['search_query']}")
        audio_path = youtube.download_audio(
            track_info['search_query'],
            f"{track_info['artists']} - {track_info['name']}"
        )
        
        if not audio_path:
            await status_msg.edit_text(
                "❌ Не вдалося завантажити трек з YouTube.\n\n"
                "💡 Можливі причини:\n"
                "• Відео недоступне або обмежене\n"
                "• YouTube заблокував доступ\n"
                "Спробуй:\n"
                "1. Надіслати інший трек\n"
                "2. Використати пряме посилання на Spotify",
                parse_mode=ParseMode.HTML
            )
            return
        
        # Відправляємо аудіо файл
        await status_msg.edit_text("📤 Відправляю аудіо...")
        
        # Форматуємо тривалість треку
        duration_ms = track_info.get('duration_ms', 0)
        duration_sec = duration_ms // 1000
        minutes = duration_sec // 60
        seconds = duration_sec % 60
        duration_str = f"{minutes}:{seconds:02d}"
        
        # Отримуємо розмір файлу
        file_size = os.path.getsize(audio_path)
        file_size_mb = file_size / (1024 * 1024)
        file_size_str = f"{file_size_mb:.2f} МБ"
        
        # Формуємо детальний опис треку
        caption = (
            f"🎵 <b>{track_info['name']}</b>\n"
            f"👤 <b>Виконавець:</b> {track_info['artists']}\n"
            f"💿 <b>Альбом:</b> {track_info['album']}\n"
            f"⏱ <b>Тривалість:</b> {duration_str}\n"
            f"📦 <b>Розмір:</b> {file_size_str}\n"
            f"🎧 <b>Якість:</b> MP3 192 kbps\n"
            f"📥 <b>Джерело:</b> YouTube\n\n"
            f"<i>Завантажено ботом @Sluhayy_bot</i> 🎶"
        )
        
        # Завантажуємо обкладинку альбому, якщо є
        thumbnail = None
        if track_info.get('image_url'):
            try:
                async with aiohttp.ClientSession() as session:
                    async with session.get(track_info['image_url']) as resp:
                        if resp.status == 200:
                            thumbnail_data = await resp.read()
                            thumbnail = BufferedInputFile(thumbnail_data, filename="cover.jpg")
            except Exception as e:
                logger.warning(f"Не вдалося завантажити обкладинку: {e}")
        
        audio_file = FSInputFile(audio_path)
        await message.answer_audio(
            audio=audio_file,
            title=track_info['name'],
            performer=track_info['artists'],
            caption=caption,
            parse_mode=ParseMode.HTML,
            thumbnail=thumbnail
        )
        
        # Видаляємо статусне повідомлення
        await status_msg.delete()
        
        # Видаляємо файл після відправки
        youtube.cleanup_file(audio_path)
        
        logger.info(f"Успішно відправлено: {track_info['name']}")
        
    except Exception as e:
        logger.error(f"Помилка при обробці запиту: {e}")
        await status_msg.edit_text(
            "❌ Виникла помилка при обробці запиту.\n"
            "Спробуй ще раз або звернись до розробника."
        )


async def main():
    """Головна функція запуску бота"""
    logger.info("Бот Sluhay запущено!")
    try:
        # Видаляємо старі оновлення та webhook
        await bot.delete_webhook(drop_pending_updates=True)
        logger.info("Webhook очищено, старі оновлення видалено")
        
        # Запускаємо polling
        await dp.start_polling(bot, allowed_updates=dp.resolve_used_update_types())
    except Exception as e:
        if "Conflict" in str(e):
            logger.error("⚠️  Виявлено конфлікт: інший екземпляр бота вже запущено!")
            logger.error("Використайте 'stop_bot.ps1' (Windows) або 'stop_bot.sh' (Linux) для зупинки")
        else:
            logger.error(f"Помилка при запуску бота: {e}")
        raise
    finally:
        await bot.session.close()


if __name__ == "__main__":
    try:
        asyncio.run(main())
    except KeyboardInterrupt:
        logger.info("Бот зупинено користувачем")
    except Exception as e:
        logger.error(f"Критична помилка: {e}")
