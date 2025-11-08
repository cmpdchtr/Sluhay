import asyncio
import logging
import aiohttp
import os
from aiogram import Bot, Dispatcher, F, types
from aiogram.filters import Command
from aiogram.types import Message, FSInputFile, BufferedInputFile, InputMediaAudio
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
        "/help - Допомога\n"
        "/test - Тестування функціоналу"
    )
    await message.answer(welcome_text, parse_mode=ParseMode.HTML)


@dp.message(Command("help"))
async def cmd_help(message: Message):
    """Обробник команди /help"""
    help_text = (
        "ℹ️ <b>Довідка по боту Sluhay</b>\n\n"
        "🎵 <b>Способи завантаження:</b>\n\n"
        "<b>1. За посиланням Spotify:</b>\n"
        "Надішли мені посилання на:\n"
        "• Трек: <code>https://open.spotify.com/track/...</code>\n"
        "• Альбом: <code>https://open.spotify.com/album/...</code>\n"
        "• Плейліст: <code>https://open.spotify.com/playlist/...</code>\n\n"
        "<b>2. За назвою (текстовий пошук):</b>\n"
        "• Трек: <code>Виконавець - Назва пісні</code>\n"
        "• Альбом: <code>альбом: Виконавець - Назва альбому</code>\n"
        "• Плейліст: <code>плейліст: Назва плейлиста</code>\n\n"
        "⏱ Завантаження зазвичай займає 10-30 секунд.\n"
        "📦 Для альбомів і плейлистів - кілька хвилин.\n\n"
        "⚠️ <b>Важливо:</b>\n"
        "• Якість аудіо: 192 kbps MP3\n"
        "• Максимальний розмір файлу: 50 МБ\n"
        "• Бот шукає трек на YouTube за даними зі Spotify\n\n"
        "🧪 <b>Тестування:</b>\n"
        "Використай /test для швидкої перевірки функціоналу без завантаження файлів.\n\n"
        "❓ Питання чи проблеми? Напиши в тех. підтримку - @cmpdchtr!"
    )
    await message.answer(help_text, parse_mode=ParseMode.HTML)


@dp.message(Command("test"))
async def cmd_test(message: Message):
    """Обробник команди /test для тестування без завантаження"""
    # Отримуємо аргумент команди
    args = message.text.split(maxsplit=1)
    
    if len(args) < 2:
        test_help = (
            "🧪 <b>Команда для тестування</b>\n\n"
            "Використання: /test [тип]\n\n"
            "<b>Доступні типи:</b>\n"
            "• <code>/test трек</code> - тестування одного треку\n"
            "• <code>/test альбом</code> - тестування альбому\n"
            "• <code>/test плейліст</code> - тестування плейлиста\n\n"
            "💡 Ця команда імітує завантаження без реального скачування файлів."
        )
        await message.answer(test_help, parse_mode=ParseMode.HTML)
        return
    
    test_type = args[1].lower().strip()
    status_msg = await message.answer("🧪 Тестування...")
    
    try:
        if test_type in ["трек", "track"]:
            # Імітація завантаження треку
            await status_msg.edit_text("🔍 Шукаю трек...")
            await asyncio.sleep(0.5)
            
            track_info = spotify.search_track("The Weeknd Blinding Lights")
            
            if track_info:
                info_text = (
                    f"✅ Знайдено трек!\n\n"
                    f"🎵 <b>{track_info['name']}</b>\n"
                    f"👤 {track_info['artists']}\n"
                    f"💿 Альбом: {track_info['album']}\n\n"
                    f"⏳ [Тестовий режим - файл не завантажується]"
                )
                await status_msg.edit_text(info_text, parse_mode=ParseMode.HTML)
                
                # Показуємо обкладинку
                if track_info.get('image_url'):
                    try:
                        async with aiohttp.ClientSession() as session:
                            async with session.get(track_info['image_url']) as resp:
                                if resp.status == 200:
                                    photo_data = await resp.read()
                                    photo = BufferedInputFile(photo_data, filename="test_cover.jpg")
                                    caption = (
                                        f"🧪 <b>Тест треку</b>\n\n"
                                        f"🎵 <b>{track_info['name']}</b>\n"
                                        f"👤 <b>Виконавець:</b> {track_info['artists']}\n"
                                        f"💿 <b>Альбом:</b> {track_info['album']}\n\n"
                                        f"✅ Всі дані отримано успішно!"
                                    )
                                    await message.answer_photo(photo=photo, caption=caption, parse_mode=ParseMode.HTML)
                                    await status_msg.delete()
                    except Exception as e:
                        logger.warning(f"Не вдалося завантажити обкладинку: {e}")
            else:
                await status_msg.edit_text("❌ Тестовий трек не знайдено.")
        
        elif test_type in ["альбом", "album"]:
            # Імітація завантаження альбому
            await status_msg.edit_text("🔍 Шукаю альбом...")
            await asyncio.sleep(0.5)
            
            search_result = spotify.search_album("The Weeknd After Hours")
            
            if search_result:
                album_info = spotify.get_album_info(search_result['url'])
                
                if album_info:
                    tracks = album_info['tracks']
                    total_tracks = len(tracks)
                    
                    # Імітація завантаження треків
                    for i in range(1, min(4, total_tracks + 1)):
                        await status_msg.edit_text(
                            f"💿 <b>{album_info['name']}</b>\n\n"
                            f"⏳ Завантаження: {i}/{total_tracks}\n"
                            f"🎵 {tracks[i-1]['name']}\n"
                            f"👤 {tracks[i-1]['artists']}\n\n"
                            f"[Тестовий режим]",
                            parse_mode=ParseMode.HTML
                        )
                        await asyncio.sleep(0.3)
                    
                    # Відправляємо обкладинку з інфо
                    if album_info.get('image_url'):
                        try:
                            async with aiohttp.ClientSession() as session:
                                async with session.get(album_info['image_url']) as resp:
                                    if resp.status == 200:
                                        photo_data = await resp.read()
                                        photo = BufferedInputFile(photo_data, filename="test_album.jpg")
                                        caption = (
                                            f"🧪 <b>Тест альбому</b>\n\n"
                                            f"💿 <b>{album_info['name']}</b>\n"
                                            f"👤 <b>Виконавець:</b> {album_info['artist']}\n"
                                            f"📅 <b>Рік:</b> {album_info['release_date']}\n"
                                            f"🎵 <b>Треків:</b> {total_tracks}\n\n"
                                            f"✅ Всі дані отримано успішно!\n"
                                            f"💡 У реальному режимі буде завантажено {total_tracks} треків."
                                        )
                                        await message.answer_photo(photo=photo, caption=caption, parse_mode=ParseMode.HTML)
                                        await status_msg.delete()
                        except Exception as e:
                            logger.warning(f"Не вдалося завантажити обкладинку: {e}")
                else:
                    await status_msg.edit_text("❌ Не вдалося отримати інформацію про альбом.")
            else:
                await status_msg.edit_text("❌ Тестовий альбом не знайдено.")
        
        elif test_type in ["плейліст", "плейлист", "playlist"]:
            # Імітація завантаження плейлиста
            await status_msg.edit_text("🔍 Шукаю плейліст...")
            await asyncio.sleep(0.5)
            
            search_result = spotify.search_playlist("Today's Top Hits")
            
            if search_result:
                playlist_info = spotify.get_playlist_info(search_result['url'])
                
                if playlist_info:
                    tracks = playlist_info['tracks']
                    total_tracks = len(tracks)
                    
                    # Імітація завантаження треків
                    for i in range(1, min(4, total_tracks + 1)):
                        await status_msg.edit_text(
                            f"📋 <b>{playlist_info['name']}</b>\n\n"
                            f"⏳ Завантаження: {i}/{total_tracks}\n"
                            f"🎵 {tracks[i-1]['name']}\n"
                            f"👤 {tracks[i-1]['artists']}\n\n"
                            f"[Тестовий режим]",
                            parse_mode=ParseMode.HTML
                        )
                        await asyncio.sleep(0.3)
                    
                    # Відправляємо обкладинку з інфо
                    if playlist_info.get('image_url'):
                        try:
                            async with aiohttp.ClientSession() as session:
                                async with session.get(playlist_info['image_url']) as resp:
                                    if resp.status == 200:
                                        photo_data = await resp.read()
                                        photo = BufferedInputFile(photo_data, filename="test_playlist.jpg")
                                        caption = (
                                            f"🧪 <b>Тест плейлиста</b>\n\n"
                                            f"📋 <b>{playlist_info['name']}</b>\n"
                                            f"👤 <b>Автор:</b> {playlist_info['owner']}\n"
                                            f"🎵 <b>Треків:</b> {total_tracks}\n\n"
                                            f"✅ Всі дані отримано успішно!\n"
                                            f"💡 У реальному режимі буде завантажено {total_tracks} треків."
                                        )
                                        await message.answer_photo(photo=photo, caption=caption, parse_mode=ParseMode.HTML)
                                        await status_msg.delete()
                        except Exception as e:
                            logger.warning(f"Не вдалося завантажити обкладинку: {e}")
                else:
                    await status_msg.edit_text("❌ Не вдалося отримати інформацію про плейліст.")
            else:
                await status_msg.edit_text("❌ Тестовий плейліст не знайдено.")
        
        else:
            await status_msg.edit_text(
                f"❌ Невідомий тип тесту: {test_type}\n\n"
                f"Використай: /test трек, /test альбом, або /test плейліст"
            )
    
    except Exception as e:
        logger.error(f"Помилка при тестуванні: {e}")
        await status_msg.edit_text(
            "❌ Виникла помилка при тестуванні.\n"
            "Спробуй ще раз."
        )


@dp.message(F.text)
async def handle_message(message: Message):
    """Обробник текстових повідомлень"""
    user_input = message.text.strip()
    
    # Відправляємо повідомлення про обробку
    status_msg = await message.answer("🔍 Аналізую запит...")
    
    try:
        # Перевіряємо, чи це посилання Spotify
        if "spotify.com" in user_input or "spotify:" in user_input:
            # Визначаємо тип посилання
            if "/playlist/" in user_input or ":playlist:" in user_input:
                await handle_playlist(message, status_msg, user_input)
                return
            elif "/album/" in user_input or ":album:" in user_input:
                await handle_album(message, status_msg, user_input)
                return
            elif "/track/" in user_input or ":track:" in user_input:
                await handle_track(message, status_msg, user_input)
                return
            else:
                await status_msg.edit_text(
                    "❌ Непідтримуваний тип посилання Spotify.\n"
                    "Підтримуються: треки, альбоми та плейлисти."
                )
                return
        else:
            # Перевіряємо префікси для текстового пошуку
            lower_input = user_input.lower()
            
            if lower_input.startswith(("альбом:", "album:")):
                # Пошук альбому
                query = user_input.split(":", 1)[1].strip()
                await handle_album(message, status_msg, query, is_search=True)
                return
            elif lower_input.startswith(("плейліст:", "playlist:", "плейлист:")):
                # Пошук плейлиста
                query = user_input.split(":", 1)[1].strip()
                await handle_playlist(message, status_msg, query, is_search=True)
                return
            else:
                # Пошук треку за текстовим запитом
                await handle_track(message, status_msg, user_input, is_search=True)
                return
            
    except Exception as e:
        logger.error(f"Помилка при обробці запиту: {e}")
        await status_msg.edit_text(
            "❌ Виникла помилка при обробці запиту.\n"
            "Спробуй ще раз або звернись до розробника."
        )


async def handle_track(message: Message, status_msg: Message, user_input: str, is_search: bool = False):
    """Обробка одного треку"""
    try:
        track_info = None
        
        if is_search:
            logger.info(f"Пошук треку: {user_input}")
            await status_msg.edit_text("🔍 Шукаю трек...")
            track_info = spotify.search_track(user_input)
            
            if not track_info:
                await status_msg.edit_text(
                    "❌ Трек не знайдено на Spotify.\n"
                    "Спробуй інший запит або надішли посилання."
                )
                return
        else:
            logger.info(f"Обробка Spotify URL: {user_input}")
            await status_msg.edit_text("🔍 Шукаю трек...")
            track_info = spotify.get_track_info(user_input)
            
            if not track_info:
                await status_msg.edit_text(
                    "❌ Не вдалося отримати інформацію про трек зі Spotify.\n"
                    "Перевір посилання і спробуй ще раз."
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


async def handle_playlist(message: types.Message, status_msg: types.Message, user_input: str, is_search: bool = False):
    """Обробка плейлиста зі Spotify"""
    try:
        playlist_url = user_input
        
        # Якщо це текстовий пошук, спочатку шукаємо плейліст
        if is_search:
            logger.info(f"Пошук плейлиста: {user_input}")
            await status_msg.edit_text("🔍 Шукаю плейліст...")
            
            search_result = spotify.search_playlist(user_input)
            if not search_result:
                await status_msg.edit_text(
                    "❌ Плейліст не знайдено.\n\n"
                    "💡 Спробуй:\n"
                    "• Інший запит\n"
                    "• Пряме посилання на плейліст Spotify"
                )
                return
            
            playlist_url = search_result['url']
        
        # Отримуємо інформацію про плейліст
        playlist_info = spotify.get_playlist_info(playlist_url)
        
        if not playlist_info:
            await status_msg.edit_text(
                "❌ Не вдалося отримати інформацію про плейліст зі Spotify.\n"
                "Перевір посилання і спробуй ще раз."
            )
            return
        
        tracks = playlist_info['tracks']
        total_tracks = len(tracks)
        
        # Виводимо інформацію про плейліст
        info_text = (
            f"✅ Знайдено плейліст!\n\n"
            f"📋 <b>{playlist_info['name']}</b>\n"
            f"👤 {playlist_info['owner']}\n"
            f"🎵 Треків: {total_tracks}\n\n"
            f"⏳ Починаю завантаження..."
        )
        await status_msg.edit_text(info_text, parse_mode=ParseMode.HTML)
        
        # Завантажуємо всі треки
        downloaded_files = []
        failed_tracks = []
        
        for index, track_info in enumerate(tracks, 1):
            try:
                await status_msg.edit_text(
                    f"📋 <b>{playlist_info['name']}</b>\n\n"
                    f"⏳ Завантаження: {index}/{total_tracks}\n"
                    f"🎵 {track_info['name']}\n"
                    f"👤 {track_info['artists']}",
                    parse_mode=ParseMode.HTML
                )
                
                # Завантажуємо аудіо з YouTube
                audio_path = youtube.download_audio(
                    track_info['search_query'],
                    f"{track_info['artists']} - {track_info['name']}"
                )
                
                if audio_path:
                    downloaded_files.append({
                        'path': audio_path,
                        'title': track_info['name'],
                        'performer': track_info['artists']
                    })
                else:
                    failed_tracks.append(track_info['name'])
                    logger.warning(f"Пропущено трек: {track_info['name']}")
                
            except Exception as e:
                failed_tracks.append(track_info['name'])
                logger.error(f"Помилка при завантаженні треку {track_info['name']}: {e}")
        
        # Відправляємо завантажені файли групами по 10
        if downloaded_files:
            await status_msg.edit_text(
                f"📋 <b>{playlist_info['name']}</b>\n\n"
                f"✅ Завантажено: {len(downloaded_files)}/{total_tracks}\n"
                f"📤 Відправляю файли...",
                parse_mode=ParseMode.HTML
            )
            
            # Спочатку відправляємо обкладинку плейлиста з описом
            if playlist_info.get('image_url'):
                try:
                    caption = (
                        f"📋 <b>{playlist_info['name']}</b>\n"
                        f"👤 <b>Автор:</b> {playlist_info['owner']}\n"
                        f"🎵 <b>Треків:</b> {total_tracks}\n"
                        f"✅ <b>Завантажено:</b> {len(downloaded_files)}/{total_tracks}"
                    )
                    
                    if failed_tracks:
                        caption += f"\n❌ <b>Пропущено:</b> {len(failed_tracks)}"
                    
                    async with aiohttp.ClientSession() as session:
                        async with session.get(playlist_info['image_url']) as resp:
                            if resp.status == 200:
                                photo_data = await resp.read()
                                photo = BufferedInputFile(photo_data, filename="playlist_cover.jpg")
                                await message.answer_photo(photo=photo, caption=caption, parse_mode=ParseMode.HTML)
                except Exception as e:
                    logger.warning(f"Не вдалося відправити обкладинку плейлиста: {e}")
            
            # Завантажуємо обкладинку для треків
            thumbnail = None
            if playlist_info.get('image_url'):
                try:
                    async with aiohttp.ClientSession() as session:
                        async with session.get(playlist_info['image_url']) as resp:
                            if resp.status == 200:
                                thumbnail_data = await resp.read()
                                thumbnail = BufferedInputFile(thumbnail_data, filename="cover.jpg")
                except Exception as e:
                    logger.warning(f"Не вдалося завантажити обкладинку: {e}")
            
            # Telegram дозволяє відправляти до 10 медіа-файлів за раз
            for i in range(0, len(downloaded_files), 10):
                batch = downloaded_files[i:i+10]
                media_group = []
                
                for file_info in batch:
                    audio_file = FSInputFile(file_info['path'])
                    
                    media_group.append(InputMediaAudio(
                        media=audio_file,
                        title=file_info['title'],
                        performer=file_info['performer'],
                        thumbnail=thumbnail
                    ))
                
                # Відправляємо групу
                await message.answer_media_group(media=media_group)
                
                # Видаляємо файли після відправки
                for file_info in batch:
                    youtube.cleanup_file(file_info['path'])
            
            # Видаляємо статусне повідомлення
            await status_msg.delete()
        else:
            await status_msg.edit_text(
                "❌ Не вдалося завантажити жодного треку з плейлиста.",
                parse_mode=ParseMode.HTML
            )
        
    except Exception as e:
        logger.error(f"Помилка при обробці плейлиста: {e}")
        await status_msg.edit_text(
            "❌ Виникла помилка при обробці плейлиста.\n"
            "Спробуй ще раз або звернись до розробника."
        )


async def handle_album(message: types.Message, status_msg: types.Message, user_input: str, is_search: bool = False):
    """Обробка альбому зі Spotify"""
    try:
        album_url = user_input
        
        # Якщо це текстовий пошук, спочатку шукаємо альбом
        if is_search:
            logger.info(f"Пошук альбому: {user_input}")
            await status_msg.edit_text("🔍 Шукаю альбом...")
            
            search_result = spotify.search_album(user_input)
            if not search_result:
                await status_msg.edit_text(
                    "❌ Альбом не знайдено.\n\n"
                    "💡 Спробуй:\n"
                    "• Інший запит\n"
                    "• Пряме посилання на альбом Spotify"
                )
                return
            
            album_url = search_result['url']
        
        # Отримуємо інформацію про альбом
        album_info = spotify.get_album_info(album_url)
        
        if not album_info:
            await status_msg.edit_text(
                "❌ Не вдалося отримати інформацію про альбом зі Spotify.\n"
                "Перевір посилання і спробуй ще раз."
            )
            return
        
        tracks = album_info['tracks']
        total_tracks = len(tracks)
        
        # Виводимо інформацію про альбом
        info_text = (
            f"✅ Знайдено альбом!\n\n"
            f"💿 <b>{album_info['name']}</b>\n"
            f"👤 {album_info['artist']}\n"
            f"📅 {album_info['release_date']}\n"
            f"🎵 Треків: {total_tracks}\n\n"
            f"⏳ Починаю завантаження..."
        )
        await status_msg.edit_text(info_text, parse_mode=ParseMode.HTML)
        
        # Завантажуємо всі треки
        downloaded_files = []
        failed_tracks = []
        
        for index, track_info in enumerate(tracks, 1):
            try:
                await status_msg.edit_text(
                    f"💿 <b>{album_info['name']}</b>\n\n"
                    f"⏳ Завантаження: {index}/{total_tracks}\n"
                    f"🎵 {track_info['name']}\n"
                    f"👤 {track_info['artists']}",
                    parse_mode=ParseMode.HTML
                )
                
                # Завантажуємо аудіо з YouTube
                audio_path = youtube.download_audio(
                    track_info['search_query'],
                    f"{track_info['artists']} - {track_info['name']}"
                )
                
                if audio_path:
                    downloaded_files.append({
                        'path': audio_path,
                        'title': track_info['name'],
                        'performer': track_info['artists']
                    })
                else:
                    failed_tracks.append(track_info['name'])
                    logger.warning(f"Пропущено трек: {track_info['name']}")
                
            except Exception as e:
                failed_tracks.append(track_info['name'])
                logger.error(f"Помилка при завантаженні треку {track_info['name']}: {e}")
        
        # Відправляємо завантажені файли групами по 10
        if downloaded_files:
            await status_msg.edit_text(
                f"💿 <b>{album_info['name']}</b>\n\n"
                f"✅ Завантажено: {len(downloaded_files)}/{total_tracks}\n"
                f"📤 Відправляю файли...",
                parse_mode=ParseMode.HTML
            )
            
            # Спочатку відправляємо обкладинку альбому з описом
            if album_info.get('image_url'):
                try:
                    caption = (
                        f"💿 <b>{album_info['name']}</b>\n"
                        f"👤 <b>Виконавець:</b> {album_info['artist']}\n"
                        f"📅 <b>Рік:</b> {album_info['release_date']}\n"
                        f"🎵 <b>Треків:</b> {total_tracks}\n"
                        f"✅ <b>Завантажено:</b> {len(downloaded_files)}/{total_tracks}"
                    )
                    
                    if failed_tracks:
                        caption += f"\n❌ <b>Пропущено:</b> {len(failed_tracks)}"
                    
                    async with aiohttp.ClientSession() as session:
                        async with session.get(album_info['image_url']) as resp:
                            if resp.status == 200:
                                photo_data = await resp.read()
                                photo = BufferedInputFile(photo_data, filename="album_cover.jpg")
                                await message.answer_photo(photo=photo, caption=caption, parse_mode=ParseMode.HTML)
                except Exception as e:
                    logger.warning(f"Не вдалося відправити обкладинку альбому: {e}")
            
            # Завантажуємо обкладинку для треків
            thumbnail = None
            if album_info.get('image_url'):
                try:
                    async with aiohttp.ClientSession() as session:
                        async with session.get(album_info['image_url']) as resp:
                            if resp.status == 200:
                                thumbnail_data = await resp.read()
                                thumbnail = BufferedInputFile(thumbnail_data, filename="cover.jpg")
                except Exception as e:
                    logger.warning(f"Не вдалося завантажити обкладинку: {e}")
            
            # Telegram дозволяє відправляти до 10 медіа-файлів за раз
            for i in range(0, len(downloaded_files), 10):
                batch = downloaded_files[i:i+10]
                media_group = []
                
                for file_info in batch:
                    audio_file = FSInputFile(file_info['path'])
                    
                    media_group.append(InputMediaAudio(
                        media=audio_file,
                        title=file_info['title'],
                        performer=file_info['performer'],
                        thumbnail=thumbnail
                    ))
                
                # Відправляємо групу
                await message.answer_media_group(media=media_group)
                
                # Видаляємо файли після відправки
                for file_info in batch:
                    youtube.cleanup_file(file_info['path'])
            
            # Видаляємо статусне повідомлення
            await status_msg.delete()
        else:
            await status_msg.edit_text(
                "❌ Не вдалося завантажити жодного треку з альбому.",
                parse_mode=ParseMode.HTML
            )
        
    except Exception as e:
        logger.error(f"Помилка при обробці альбому: {e}")
        await status_msg.edit_text(
            "❌ Виникла помилка при обробці альбому.\n"
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
