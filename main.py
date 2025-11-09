import asyncio
import logging
import aiohttp
import os
import hashlib
import json
from aiogram import Bot, Dispatcher, F, types
from aiogram.filters import Command, CommandStart
from aiogram.types import Message, FSInputFile, BufferedInputFile, InputMediaAudio, InlineKeyboardMarkup, InlineKeyboardButton, CallbackQuery, ReplyKeyboardMarkup, KeyboardButton, ReplyKeyboardRemove
from aiogram.enums import ParseMode
from aiogram.fsm.context import FSMContext
from aiogram.fsm.state import State, StatesGroup
from aiogram.fsm.storage.memory import MemoryStorage

import config
from spotify_service import SpotifyService
from soundcloud_downloader import SoundCloudDownloader


# Налаштування логування
logging.basicConfig(
    level=logging.INFO,
    format='%(asctime)s - %(name)s - %(levelname)s - %(message)s'
)
logger = logging.getLogger(__name__)

# Ініціалізація бота з FSM storage
storage = MemoryStorage()
bot = Bot(token=config.TELEGRAM_BOT_TOKEN)
dp = Dispatcher(storage=storage)

# Ініціалізація сервісів
spotify = SpotifyService()
soundcloud = SoundCloudDownloader()

# Файл для збереження налаштувань
SETTINGS_FILE = "user_settings.json"

# Налаштування користувачів
user_settings = {}

def load_user_settings():
    """Завантажити налаштування користувачів з файлу"""
    global user_settings
    try:
        if os.path.exists(SETTINGS_FILE):
            with open(SETTINGS_FILE, 'r', encoding='utf-8') as f:
                # Конвертуємо ключі назад в int
                loaded = json.load(f)
                user_settings = {int(k): v for k, v in loaded.items()}
                logger.info(f"Завантажено налаштування для {len(user_settings)} користувачів")
        else:
            user_settings = {}
            logger.info("Файл налаштувань не знайдено, створено новий")
    except Exception as e:
        logger.error(f"Помилка при завантаженні налаштувань: {e}")
        user_settings = {}

def save_user_settings():
    """Зберегти налаштування користувачів у файл"""
    try:
        # Конвертуємо ключі в string для JSON
        to_save = {str(k): v for k, v in user_settings.items()}
        with open(SETTINGS_FILE, 'w', encoding='utf-8') as f:
            json.dump(to_save, f, ensure_ascii=False, indent=2)
        logger.info(f"Збережено налаштування для {len(user_settings)} користувачів")
    except Exception as e:
        logger.error(f"Помилка при збереженні налаштувань: {e}")

def get_user_settings(user_id: int) -> dict:
    """Отримати налаштування користувача"""
    if user_id not in user_settings:
        user_settings[user_id] = {
            'bitrate': 128,  # За замовчуванням 128 kbps
            'favorites': {
                'tracks': [],      # [{'name': str, 'artist': str, 'url': str, 'saved_at': str}]
                'albums': [],      # [{'name': str, 'artist': str, 'url': str, 'saved_at': str}]
                'playlists': []    # [{'name': str, 'owner': str, 'url': str, 'saved_at': str}]
            }
        }
        save_user_settings()  # Зберігаємо після створення
    return user_settings[user_id]

def get_user_bitrate(user_id: int) -> int:
    """Отримати бітрейт користувача"""
    settings = get_user_settings(user_id)
    return settings['bitrate']

def set_user_bitrate(user_id: int, bitrate: int):
    """Встановити бітрейт користувача"""
    settings = get_user_settings(user_id)
    settings['bitrate'] = bitrate
    save_user_settings()  # Зберігаємо після зміни
    logger.info(f"Користувач {user_id} встановив бітрейт: {bitrate} kbps")

def add_to_favorites(user_id: int, item_type: str, item_data: dict):
    """Додати до збережених"""
    from datetime import datetime
    
    settings = get_user_settings(user_id)
    item_data['saved_at'] = datetime.now().strftime("%Y-%m-%d %H:%M:%S")
    
    if item_type == 'track':
        # Перевірка чи вже збережено
        if not any(t['url'] == item_data['url'] for t in settings['favorites']['tracks']):
            settings['favorites']['tracks'].append(item_data)
            save_user_settings()  # Зберігаємо після додавання
            logger.info(f"Користувач {user_id} зберіг трек: {item_data['name']}")
            return True
    elif item_type == 'album':
        if not any(a['url'] == item_data['url'] for a in settings['favorites']['albums']):
            settings['favorites']['albums'].append(item_data)
            save_user_settings()  # Зберігаємо після додавання
            logger.info(f"Користувач {user_id} зберіг альбом: {item_data['name']}")
            return True
    elif item_type == 'playlist':
        if not any(p['url'] == item_data['url'] for p in settings['favorites']['playlists']):
            settings['favorites']['playlists'].append(item_data)
            save_user_settings()  # Зберігаємо після додавання
            logger.info(f"Користувач {user_id} зберіг плейліст: {item_data['name']}")
            return True
    
    return False  # Вже було збережено

def remove_from_favorites(user_id: int, item_type: str, item_url: str):
    """Видалити зі збережених"""
    settings = get_user_settings(user_id)
    
    if item_type == 'track':
        settings['favorites']['tracks'] = [t for t in settings['favorites']['tracks'] if t['url'] != item_url]
    elif item_type == 'album':
        settings['favorites']['albums'] = [a for a in settings['favorites']['albums'] if a['url'] != item_url]
    elif item_type == 'playlist':
        settings['favorites']['playlists'] = [p for p in settings['favorites']['playlists'] if p['url'] != item_url]
    
    save_user_settings()  # Зберігаємо після видалення
    logger.info(f"Користувач {user_id} видалив {item_type} зі збережених")

def get_favorites(user_id: int, item_type: str = None) -> dict:
    """Отримати збережені"""
    settings = get_user_settings(user_id)
    
    if item_type:
        return settings['favorites'].get(f"{item_type}s", [])
    return settings['favorites']


# FSM States для пошуку
class SearchStates(StatesGroup):
    waiting_for_track = State()
    waiting_for_album = State()
    waiting_for_playlist = State()
    downloading_album = State()
    downloading_playlist = State()


def get_main_menu_keyboard():
    """Головне меню з кнопками"""
    keyboard = InlineKeyboardMarkup(inline_keyboard=[
        [
            InlineKeyboardButton(text="🔍", callback_data="search"),
            InlineKeyboardButton(text="🔥", callback_data="top50"),
            InlineKeyboardButton(text="⭐", callback_data="favorites")
        ],
        [
            InlineKeyboardButton(text="⚙️ Налаштунки", callback_data="settings"),
            InlineKeyboardButton(text="👤 Профіль", callback_data="profile")
        ]
    ])
    return keyboard


def get_search_menu_keyboard():
    """Меню пошуку"""
    keyboard = InlineKeyboardMarkup(inline_keyboard=[
        [InlineKeyboardButton(text="🎵 Пошук Треку", callback_data="search_track")],
        [InlineKeyboardButton(text="💿 Пошук Альбому", callback_data="search_album")],
        [InlineKeyboardButton(text="📋 Пошук Плейліста", callback_data="search_playlist")],
        [InlineKeyboardButton(text="◀️ Назад", callback_data="back_to_main")]
    ])
    return keyboard


def get_settings_menu_keyboard():
    """Меню налаштувань"""
    keyboard = InlineKeyboardMarkup(inline_keyboard=[
        [InlineKeyboardButton(text="🎧 Встановити бітрейт", callback_data="set_bitrate")],
        [InlineKeyboardButton(text="🗑 Очистити історію чата", callback_data="clear_history")],
        [InlineKeyboardButton(text="◀️ Назад", callback_data="back_to_main")]
    ])
    return keyboard


def get_bitrate_menu_keyboard():
    """Меню вибору бітрейту"""
    keyboard = InlineKeyboardMarkup(inline_keyboard=[
        [InlineKeyboardButton(text="🔊 128 kbps (Рекомендовано)", callback_data="bitrate_128")],
        [InlineKeyboardButton(text="🔉 96 kbps (Економія трафіку)", callback_data="bitrate_96")],
        [InlineKeyboardButton(text="🔈 64 kbps (Низька якість)", callback_data="bitrate_64")],
        [InlineKeyboardButton(text="🔊 192 kbps (Висока якість)", callback_data="bitrate_192")],
        [InlineKeyboardButton(text="🔊 320 kbps (Максимальна)", callback_data="bitrate_320")],
        [InlineKeyboardButton(text="◀️ Назад", callback_data="settings")]
    ])
    return keyboard


@dp.message(CommandStart())
async def cmd_start(message: Message):
    """Обробник команди /start"""
    user_name = message.from_user.first_name or "друже"
    welcome_text = f"👋 Привіт, {user_name}! Що будемо слухати сьогодні?"
    
    await message.answer(
        welcome_text,
        reply_markup=get_main_menu_keyboard()
    )


# Callback handlers
@dp.callback_query(F.data == "search")
async def callback_search(callback: CallbackQuery):
    """Обробник кнопки Пошук"""
    await callback.message.edit_text(
        "🔍 <b>Виберіть тип пошуку:</b>",
        parse_mode=ParseMode.HTML,
        reply_markup=get_search_menu_keyboard()
    )
    await callback.answer()


@dp.callback_query(F.data == "back_to_main")
async def callback_back_to_main(callback: CallbackQuery, state: FSMContext):
    """Повернення до головного меню"""
    await state.clear()
    user_name = callback.from_user.first_name or "друже"
    
    # Спробуємо редагувати повідомлення
    try:
        await callback.message.edit_text(
            f"👋 Привіт, {user_name}! Що будемо слухати сьогодні?",
            reply_markup=get_main_menu_keyboard()
        )
    except:
        # Якщо не вийшло - відправляємо нове
        await callback.message.answer(
            f"👋 Привіт, {user_name}! Що будемо слухати сьогодні?",
            reply_markup=get_main_menu_keyboard()
        )
    
    await callback.answer()


@dp.callback_query(F.data == "search_track")
async def callback_search_track(callback: CallbackQuery, state: FSMContext):
    """Початок пошуку треку"""
    await state.set_state(SearchStates.waiting_for_track)
    
    # Створюємо Reply клавіатуру з кнопкою відміни та placeholder
    cancel_keyboard = ReplyKeyboardMarkup(
        keyboard=[[KeyboardButton(text="❌ Скасувати")]],
        resize_keyboard=True,
        input_field_placeholder="Виконавець - Трек"
    )
    
    await callback.message.answer(
        "🎵 <b>Пошук треку</b>\n\n"
        "📝 <i>Введи назву треку або посилання Spotify</i>",
        parse_mode=ParseMode.HTML,
        reply_markup=cancel_keyboard
    )
    
    await callback.answer()


@dp.callback_query(F.data == "search_album")
async def callback_search_album(callback: CallbackQuery, state: FSMContext):
    """Початок пошуку альбому"""
    await state.set_state(SearchStates.waiting_for_album)
    
    # Створюємо Reply клавіатуру з кнопкою відміни та placeholder
    cancel_keyboard = ReplyKeyboardMarkup(
        keyboard=[[KeyboardButton(text="❌ Скасувати")]],
        resize_keyboard=True,
        input_field_placeholder="Виконавець - Альбом"
    )
    
    await callback.message.answer(
        "💿 <b>Пошук альбому</b>\n\n"
        "📝 <i>Введи назву альбому або посилання Spotify</i>",
        parse_mode=ParseMode.HTML,
        reply_markup=cancel_keyboard
    )
    
    await callback.answer()


@dp.callback_query(F.data == "search_playlist")
async def callback_search_playlist(callback: CallbackQuery, state: FSMContext):
    """Початок пошуку плейліста"""
    await state.set_state(SearchStates.waiting_for_playlist)
    
    # Створюємо Reply клавіатуру з кнопкою відміни та placeholder
    cancel_keyboard = ReplyKeyboardMarkup(
        keyboard=[[KeyboardButton(text="❌ Скасувати")]],
        resize_keyboard=True,
        input_field_placeholder="Плейліст"
    )
    
    await callback.message.answer(
        "📋 <b>Пошук плейліста</b>\n\n"
        "📝 <i>Введи назву плейліста або посилання Spotify</i>",
        parse_mode=ParseMode.HTML,
        reply_markup=cancel_keyboard
    )
    
    await callback.answer()


# Заглушки для інших кнопок
@dp.callback_query(F.data == "top50")
async def callback_top50(callback: CallbackQuery):
    """ТОП-50 (поки заглушка)"""
    await callback.answer("🔥 ТОП-50 - скоро буде доступно!", show_alert=True)


@dp.callback_query(F.data == "settings")
async def callback_settings(callback: CallbackQuery):
    """Налаштування"""
    await callback.message.edit_text(
        "⚙️ <b>Налаштування бота</b>\n\n"
        "Виберіть опцію для налаштування:",
        parse_mode=ParseMode.HTML,
        reply_markup=get_settings_menu_keyboard()
    )
    await callback.answer()


@dp.callback_query(F.data == "set_bitrate")
async def callback_set_bitrate(callback: CallbackQuery):
    """Меню вибору бітрейту"""
    current_bitrate = get_user_bitrate(callback.from_user.id)
    
    await callback.message.edit_text(
        "🎧 <b>Вибір якості аудіо</b>\n\n"
        "Оберіть бажаний бітрейт для завантаження:\n\n"
        "• <b>320 kbps</b> - Максимальна якість, великий розмір\n"
        "• <b>192 kbps</b> - Висока якість\n"
        "• <b>128 kbps</b> - Оптимальне співвідношення (рекомендовано)\n"
        "• <b>96 kbps</b> - Економія трафіку\n"
        "• <b>64 kbps</b> - Мінімальний розмір файлу\n\n"
        f"💡 Поточний бітрейт: <b>{current_bitrate} kbps</b>",
        parse_mode=ParseMode.HTML,
        reply_markup=get_bitrate_menu_keyboard()
    )
    await callback.answer()


@dp.callback_query(F.data.startswith("bitrate_"))
async def callback_bitrate_selected(callback: CallbackQuery):
    """Обробка вибору бітрейту"""
    bitrate = int(callback.data.split("_")[1])
    user_id = callback.from_user.id
    
    # Зберігаємо вибраний бітрейт
    set_user_bitrate(user_id, bitrate)
    
    await callback.message.edit_text(
        f"✅ <b>Бітрейт встановлено: {bitrate} kbps</b>\n\n"
        f"Всі наступні завантаження будуть у цій якості.\n\n"
        f"💡 Ви можете змінити це налаштування в будь-який час.",
        parse_mode=ParseMode.HTML,
        reply_markup=get_settings_menu_keyboard()
    )
    await callback.answer(f"✅ Бітрейт {bitrate} kbps встановлено!")


@dp.callback_query(F.data == "clear_history")
async def callback_clear_history(callback: CallbackQuery):
    """Очистка історії чата - підтвердження"""
    keyboard = InlineKeyboardMarkup(inline_keyboard=[
        [
            InlineKeyboardButton(text="✅ Так, очистити", callback_data="clear_history_confirm"),
            InlineKeyboardButton(text="❌ Скасувати", callback_data="settings")
        ]
    ])
    
    await callback.message.edit_text(
        "🗑 <b>Очистити історію чата?</b>\n\n"
        "⚠️ Ця дія видалить:\n"
        "• Всі повідомлення бота в цьому чаті\n"
        "• Всі завантажені файли з цього чата\n"
        "• Ваші налаштування (бітрейт тощо)\n\n"
        "💡 Повідомлення які ви надіслали залишаться.\n\n"
        "Ви впевнені?",
        parse_mode=ParseMode.HTML,
        reply_markup=keyboard
    )
    await callback.answer()


@dp.callback_query(F.data == "clear_history_confirm")
async def callback_clear_history_confirm(callback: CallbackQuery):
    """Виконання очистки історії"""
    try:
        chat_id = callback.message.chat.id
        user_id = callback.from_user.id
        
        await callback.answer("🗑 Видаляю повідомлення...", show_alert=False)
        
        # Зберігаємо поточне повідомлення
        current_msg_id = callback.message.message_id
        
        # Отримуємо історію повідомлень
        deleted_count = 0
        errors_count = 0
        
        # Telegram дозволяє видаляти повідомлення тільки окремо
        # Спробуємо видалити останні 100 повідомлень бота
        for i in range(100):
            try:
                # Видаляємо повідомлення починаючи з поточного і йдучи назад
                msg_id = current_msg_id - i
                if msg_id > 0:
                    await bot.delete_message(chat_id=chat_id, message_id=msg_id)
                    deleted_count += 1
                    # Невелика пауза щоб не trigger rate limit
                    if i % 10 == 0:
                        await asyncio.sleep(0.1)
            except Exception as e:
                errors_count += 1
                # Якщо багато помилок підряд - зупиняємось
                if errors_count > 20:
                    break
        
        # Очищаємо налаштування користувача
        if user_id in user_settings:
            del user_settings[user_id]
        
        # Відправляємо повідомлення про результат
        result_msg = await callback.message.answer(
            f"✅ <b>Історія очищена!</b>\n\n"
            f"🗑 Видалено повідомлень: {deleted_count}\n"
            f"💾 Налаштування скинуті\n\n"
            f"Бот готовий до роботи! 🎵",
            parse_mode=ParseMode.HTML,
            reply_markup=get_main_menu_keyboard()
        )
        
        logger.info(f"Користувач {user_id} очистив історію. Видалено: {deleted_count} повідомлень")
        
    except Exception as e:
        logger.error(f"Помилка при очистці історії: {e}")
        await callback.message.answer(
            "❌ Виникла помилка при очистці історії.\n"
            "Спробуйте ще раз пізніше.",
            reply_markup=get_settings_menu_keyboard()
        )


@dp.callback_query(F.data == "profile")
async def callback_profile(callback: CallbackQuery):
    """Профіль (поки заглушка)"""
    await callback.answer("👤 Профіль - скоро буде доступно!", show_alert=True)


@dp.callback_query(F.data == "favorites")
async def callback_favorites(callback: CallbackQuery):
    """Показати збережені"""
    user_id = callback.from_user.id
    favorites = get_favorites(user_id)
    
    tracks_count = len(favorites['tracks'])
    albums_count = len(favorites['albums'])
    playlists_count = len(favorites['playlists'])
    
    total = tracks_count + albums_count + playlists_count
    
    if total == 0:
        keyboard = InlineKeyboardMarkup(inline_keyboard=[
            [InlineKeyboardButton(text="🔙 Назад", callback_data="back_to_main")]
        ])
        await callback.message.edit_text(
            "⭐ <b>Збережені</b>\n\n"
            "📭 У вас поки немає збережених треків, альбомів або плейлістів.\n\n"
            "💡 Щоб зберегти, завантажте трек/альбом/плейліст і натисніть <b>⭐ Зберегти</b>",
            parse_mode=ParseMode.HTML,
            reply_markup=keyboard
        )
    else:
        keyboard = InlineKeyboardMarkup(inline_keyboard=[
            [InlineKeyboardButton(text=f"🎵 Треки ({tracks_count})", callback_data="fav_tracks")],
            [InlineKeyboardButton(text=f"💿 Альбоми ({albums_count})", callback_data="fav_albums")],
            [InlineKeyboardButton(text=f"📀 Плейлісти ({playlists_count})", callback_data="fav_playlists")],
            [InlineKeyboardButton(text="🔙 Назад", callback_data="back_to_main")]
        ])
        await callback.message.edit_text(
            f"⭐ <b>Збережені</b>\n\n"
            f"📊 Всього збережено: {total}\n\n"
            f"🎵 Треки: {tracks_count}\n"
            f"💿 Альбоми: {albums_count}\n"
            f"📀 Плейлісти: {playlists_count}",
            parse_mode=ParseMode.HTML,
            reply_markup=keyboard
        )
    
    await callback.answer()


@dp.callback_query(F.data.startswith("fav_"))
async def callback_favorites_category(callback: CallbackQuery):
    """Показати категорію збережених"""
    user_id = callback.from_user.id
    category = callback.data.split("_")[1]  # tracks, albums, playlists
    
    if category == "tracks":
        items = get_favorites(user_id, 'track')
        title = "🎵 Збережені треки"
        emoji = "🎵"
    elif category == "albums":
        items = get_favorites(user_id, 'album')
        title = "💿 Збережені альбоми"
        emoji = "💿"
    else:  # playlists
        items = get_favorites(user_id, 'playlist')
        title = "📀 Збережені плейлісти"
        emoji = "📀"
    
    if not items:
        keyboard = InlineKeyboardMarkup(inline_keyboard=[
            [InlineKeyboardButton(text="🔙 Назад", callback_data="favorites")]
        ])
        await callback.message.edit_text(
            f"{title}\n\n"
            f"📭 Порожньо",
            parse_mode=ParseMode.HTML,
            reply_markup=keyboard
        )
        await callback.answer()
        return
    
    # Формуємо список
    text = f"{title}\n\n"
    keyboard_buttons = []
    
    for idx, item in enumerate(items[:10], 1):  # Показуємо перші 10
        if category == "tracks":
            name = f"{item['artist']} - {item['name']}"
        elif category == "albums":
            name = f"{item['artist']} - {item['name']}"
        else:  # playlists
            name = f"{item['name']} by {item['owner']}"
        
        text += f"{idx}. {emoji} {name}\n"
        keyboard_buttons.append([
            InlineKeyboardButton(
                text=f"{idx}. {name[:30]}...",
                callback_data=f"load_fav_{category[:-1]}_{idx-1}"
            )
        ])
    
    if len(items) > 10:
        text += f"\n📊 Показано 10 з {len(items)}"
    
    keyboard_buttons.append([InlineKeyboardButton(text="🔙 Назад", callback_data="favorites")])
    keyboard = InlineKeyboardMarkup(inline_keyboard=keyboard_buttons)
    
    await callback.message.edit_text(
        text,
        parse_mode=ParseMode.HTML,
        reply_markup=keyboard
    )
    await callback.answer()


@dp.callback_query(F.data.startswith("load_fav_"))
async def callback_load_favorite(callback: CallbackQuery, state: FSMContext):
    """Завантажити збережений трек/альбом/плейліст"""
    parts = callback.data.split("_")
    item_type = parts[2]  # track, album, playlist
    item_index = int(parts[3])
    
    user_id = callback.from_user.id
    items = get_favorites(user_id, item_type)
    
    if item_index >= len(items):
        await callback.answer("❌ Елемент не знайдено", show_alert=True)
        return
    
    item = items[item_index]
    url = item['url']
    
    await callback.answer("⏳ Завантажую...", show_alert=False)
    
    status_msg = await callback.message.answer("⏳ Завантаження...")
    
    # Викликаємо відповідний handler
    if item_type == "track":
        await handle_track(callback.message, status_msg, url, state, is_search=False)
    elif item_type == "album":
        await handle_album(callback.message, status_msg, url, state, is_search=False)
    else:  # playlist
        await handle_playlist(callback.message, status_msg, url, state, is_search=False)


# Обробник кнопки "Скасувати"
@dp.message(F.text == "❌ Скасувати")
async def cancel_search(message: Message, state: FSMContext):
    """Скасування пошуку або завантаження"""
    current_state = await state.get_state()
    
    # Якщо йде завантаження - встановлюємо прапорець
    if current_state in [SearchStates.downloading_album, SearchStates.downloading_playlist]:
        await state.update_data(cancelled=True)
        await message.answer(
            "⏸️ Зупиняю завантаження...",
            reply_markup=ReplyKeyboardRemove()
        )
        return
    
    # Інакше - звичайне скасування пошуку
    await state.clear()
    user_name = message.from_user.first_name or "друже"
    await message.answer(
        f"❌ Пошук скасовано.\n\n"
        f"👋 {user_name}! Що будемо слухати сьогодні?",
        reply_markup=ReplyKeyboardRemove()
    )
    # Відправляємо головне меню
    await message.answer(
        "Вибери опцію:",
        reply_markup=get_main_menu_keyboard()
    )


@dp.callback_query(F.data.startswith("save_"))
async def callback_save_item(callback: CallbackQuery):
    """Збереження треку/альбому/плейліста"""
    parts = callback.data.split("_")
    item_type = parts[1]  # track, album, playlist
    item_id = "_".join(parts[2:])  # ID може містити _
    
    user_id = callback.from_user.id
    settings = get_user_settings(user_id)
    
    # Перевіряємо чи є тимчасові дані
    if 'temp_items' not in settings or item_id not in settings['temp_items']:
        await callback.answer("❌ Дані не знайдені. Спробуй завантажити ще раз.", show_alert=True)
        return
    
    item_data = settings['temp_items'][item_id]
    
    # Додаємо до збережених
    success = add_to_favorites(user_id, item_type, item_data)
    
    if success:
        await callback.answer("⭐ Збережено!", show_alert=True)
        
        # Оновлюємо кнопку
        keyboard = InlineKeyboardMarkup(inline_keyboard=[
            [InlineKeyboardButton(
                text="✅ Збережено",
                callback_data="already_saved"
            )],
            [InlineKeyboardButton(text="🔙 Головне меню", callback_data="back_to_main")]
        ])
        
        await callback.message.edit_reply_markup(reply_markup=keyboard)
    else:
        await callback.answer("ℹ️ Вже збережено раніше", show_alert=True)


@dp.callback_query(F.data == "already_saved")
async def callback_already_saved(callback: CallbackQuery):
    """Повідомлення що вже збережено"""
    await callback.answer("✅ Цей елемент вже в збережених!", show_alert=True)



@dp.message(Command("help"))
async def cmd_help(message: Message):
    """Обробник команди /help"""
    help_text = (
        "ℹ️ <b>Довідка по боту Sluhay</b>\n\n"
        "🎵 <b>Як користуватись:</b>\n\n"
        "1️⃣ Натисни кнопку <b>🔍 Пошук</b> у головному меню\n"
        "2️⃣ Вибери тип контенту (Трек / Альбом / Плейліст)\n"
        "3️⃣ Надішли посилання Spotify або назву\n"
        "4️⃣ Отримай музику! 🎶\n\n"
        "📝 <b>Приклади запитів:</b>\n"
        "• <code>The Weeknd - Blinding Lights</code>\n"
        "• <code>https://open.spotify.com/track/...</code>\n"
        "• <code>Pink Floyd - The Dark Side of the Moon</code>\n\n"
        "⚙️ <b>Технічні деталі:</b>\n"
        "• Якість: MP3 96 kbps\n"
        "• Джерело: 🟢 SoundCloud\n"
        "• Макс. розмір: 50 МБ\n\n"
        "🚀 <b>Команди:</b>\n"
        "/start - Головне меню\n"
        "/help - Ця довідка\n"
        "/test - Тестування\n\n"
        "💬 Питання? Пиши @cmpdchtr"
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


@dp.message(SearchStates.waiting_for_track)
async def process_track_search(message: Message, state: FSMContext):
    """Обробка пошуку треку після натискання кнопки"""
    user_input = message.text.strip()
    
    # Прибираємо Reply клавіатуру та відправляємо статус
    await message.answer("🔍 Аналізую запит...", reply_markup=ReplyKeyboardRemove())
    status_msg = await message.answer("⏳ Шукаю трек...")
    
    try:
        # Визначаємо тип введення
        if "spotify.com/track/" in user_input or "spotify:track:" in user_input:
            await handle_track(message, status_msg, user_input, is_search=False)
        else:
            await handle_track(message, status_msg, user_input, is_search=True)
    except Exception as e:
        logger.error(f"Помилка при пошуку треку: {e}")
        await message.answer("❌ Виникла помилка. Спробуй ще раз.")
    finally:
        await state.clear()


@dp.message(SearchStates.waiting_for_album)
async def process_album_search(message: Message, state: FSMContext):
    """Обробка пошуку альбому після натискання кнопки"""
    user_input = message.text.strip()
    
    # Прибираємо Reply клавіатуру та відправляємо статус
    await message.answer("🔍 Аналізую запит...", reply_markup=ReplyKeyboardRemove())
    status_msg = await message.answer("⏳ Шукаю альбом...")
    
    try:
        # Визначаємо тип введення
        if "spotify.com/album/" in user_input or "spotify:album:" in user_input:
            await handle_album(message, status_msg, user_input, state, is_search=False)
        else:
            await handle_album(message, status_msg, user_input, state, is_search=True)
    except Exception as e:
        logger.error(f"Помилка при пошуку альбому: {e}")
        await message.answer("❌ Виникла помилка. Спробуй ще раз.")
    finally:
        await state.clear()


@dp.message(SearchStates.waiting_for_playlist)
async def process_playlist_search(message: Message, state: FSMContext):
    """Обробка пошуку плейліста після натискання кнопки"""
    user_input = message.text.strip()
    
    # Прибираємо Reply клавіатуру та відправляємо статус
    await message.answer("🔍 Аналізую запит...", reply_markup=ReplyKeyboardRemove())
    status_msg = await message.answer("⏳ Шукаю плейліст...")
    
    try:
        # Визначаємо тип введення
        if "spotify.com/playlist/" in user_input or "spotify:playlist:" in user_input:
            await handle_playlist(message, status_msg, user_input, state, is_search=False)
        else:
            await handle_playlist(message, status_msg, user_input, state, is_search=True)
    except Exception as e:
        logger.error(f"Помилка при пошуку плейліста: {e}")
        await message.answer("❌ Виникла помилка. Спробуй ще раз.")
    finally:
        await state.clear()


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
            f"⏳ Шукаю трек на SoundCloud..."
        )
        await status_msg.edit_text(info_text, parse_mode=ParseMode.HTML)
        
        # Завантаження з SoundCloud
        user_bitrate = get_user_bitrate(message.from_user.id)
        logger.info(f"Завантаження: {track_info['search_query']} ({user_bitrate} kbps)")
        audio_path = soundcloud.download_audio(
            track_info['search_query'],
            f"{track_info['artists']} - {track_info['name']}",
            message.from_user.id,
            user_bitrate
        )
        
        if not audio_path:
            await status_msg.edit_text(
                "❌ Не вдалося завантажити трек з SoundCloud.\n\n"
                "💡 Можливі причини:\n"
                "• Трек недоступний на SoundCloud\n"
                "• Проблеми з доступом до сервісу\n"
                "Спробуй:\n"
                "1. Надіслати інший трек\n"
                "2. Використати пряме посилання на Spotify",
                parse_mode=ParseMode.HTML
            )
            return
        
        # Відправляємо аудіо файл
        await status_msg.edit_text(f"📤 Відправляю аудіо...")
        
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
            f"🎧 <b>Якість:</b> MP3 {user_bitrate} kbps\n"
            f"📥 <b>Джерело:</b> 🟢 SoundCloud\n\n"
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
        soundcloud.cleanup_file(audio_path)
        
        # Генеруємо унікальний ID для треку (хеш від назви + виконавця)
        track_id = hashlib.md5(f"{track_info['artists']}_{track_info['name']}".encode()).hexdigest()[:16]
        
        # Кнопка збереження
        save_keyboard = InlineKeyboardMarkup(inline_keyboard=[
            [InlineKeyboardButton(
                text="⭐ Зберегти трек",
                callback_data=f"save_track_{track_id}"
            )],
            [InlineKeyboardButton(text="🔙 Головне меню", callback_data="back_to_main")]
        ])
        
        # Зберігаємо інформацію про трек для можливості збереження
        settings = get_user_settings(message.from_user.id)
        if 'temp_items' not in settings:
            settings['temp_items'] = {}
        
        settings['temp_items'][track_id] = {
            'type': 'track',
            'name': track_info['name'],
            'artist': track_info['artists'],
            'url': user_input if not is_search else track_info.get('spotify_url', user_input)
        }
        
        # Показуємо меню з кнопкою збереження
        await message.answer(
            "✅ Трек відправлено!\n\n🎵 Бажаєш зберегти цей трек?",
            reply_markup=save_keyboard
        )
        
        logger.info(f"Успішно відправлено: {track_info['name']}")
        
    except Exception as e:
        logger.error(f"Помилка при обробці запиту: {e}")
        await status_msg.edit_text(
            "❌ Виникла помилка при обробці запиту.\n"
            "Спробуй ще раз або звернись до розробника."
        )


async def handle_playlist(message: types.Message, status_msg: types.Message, user_input: str, state: FSMContext = None, is_search: bool = False):
    """Обробка плейлиста зі Spotify"""
    try:
        playlist_url = user_input
        
        # Переходимо в стан завантаження (тільки якщо є state)
        if state:
            await state.set_state(SearchStates.downloading_playlist)
            await state.update_data(cancelled=False)
            
            # Показуємо кнопку скасування
            cancel_keyboard = ReplyKeyboardMarkup(
                keyboard=[[KeyboardButton(text="❌ Скасувати")]],
                resize_keyboard=True
            )
            cancel_msg = await message.answer(
                "⚠️ Завантаження розпочато...",
                reply_markup=cancel_keyboard
            )
        
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
            # Перевірка на скасування (якщо є state)
            if state:
                data = await state.get_data()
                if data.get('cancelled', False):
                    logger.info("Завантаження плейлиста скасовано користувачем")
                    await status_msg.edit_text("❌ Завантаження скасовано!")
                    await message.answer(
                        "🎵 Що далі?",
                        reply_markup=get_main_menu_keyboard()
                    )
                    # Видаляємо вже завантажені файли
                    for file_info in downloaded_files:
                        soundcloud.cleanup_file(file_info['path'])
                    return
            
            try:
                await status_msg.edit_text(
                    f"📋 <b>{playlist_info['name']}</b>\n\n"
                    f"⏳ Завантаження: {index}/{total_tracks}\n"
                    f"🎵 {track_info['name']}\n"
                    f"👤 {track_info['artists']}",
                    parse_mode=ParseMode.HTML
                )
                
                # Завантаження з SoundCloud
                user_bitrate = get_user_bitrate(message.from_user.id)
                audio_path = soundcloud.download_audio(
                    track_info['search_query'],
                    f"{track_info['artists']} - {track_info['name']}",
                    message.from_user.id,
                    user_bitrate
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
            
            # Telegram дозволяє відправляти до 10 медіа-файлів за раз
            for i in range(0, len(downloaded_files), 10):
                batch = downloaded_files[i:i+10]
                media_group = []
                
                for file_info in batch:
                    audio_file = FSInputFile(file_info['path'])
                    
                    # Не додаємо thumbnail - він не працює коректно в медіа-групах
                    # Обкладинка вже показана в окремому повідомленні вище
                    media_group.append(InputMediaAudio(
                        media=audio_file,
                        title=file_info['title'],
                        performer=file_info['performer']
                    ))
                
                # Відправляємо групу
                try:
                    await message.answer_media_group(media=media_group)
                except Exception as e:
                    logger.warning(f"Помилка при відправці медіа-групи плейлиста: {e}")
                    # Якщо не вдалося відправити групою, відправляємо по одному
                    for file_info in batch:
                        try:
                            audio_file = FSInputFile(file_info['path'])
                            await message.answer_audio(
                                audio=audio_file,
                                title=file_info['title'],
                                performer=file_info['performer']
                            )
                        except Exception as e2:
                            logger.error(f"Помилка при відправці файлу {file_info['title']}: {e2}")
                
                # Видаляємо файли після відправки
                for file_info in batch:
                    soundcloud.cleanup_file(file_info['path'])
            
            # Видаляємо статусне повідомлення
            await status_msg.delete()
            
            # Генеруємо унікальний ID для плейліста
            playlist_id = hashlib.md5(f"{playlist_info['owner']}_{playlist_info['name']}".encode()).hexdigest()[:16]
            
            # Кнопка збереження плейліста
            save_keyboard = InlineKeyboardMarkup(inline_keyboard=[
                [InlineKeyboardButton(
                    text="⭐ Зберегти плейліст",
                    callback_data=f"save_playlist_{playlist_id}"
                )],
                [InlineKeyboardButton(text="🔙 Головне меню", callback_data="back_to_main")]
            ])
            
            # Зберігаємо інформацію про плейліст
            settings = get_user_settings(message.from_user.id)
            if 'temp_items' not in settings:
                settings['temp_items'] = {}
            
            settings['temp_items'][playlist_id] = {
                'type': 'playlist',
                'name': playlist_info['name'],
                'owner': playlist_info['owner'],
                'url': user_input
            }
            
            # Показуємо меню (прибираємо Reply клавіатуру)
            await message.answer(
                f"✅ Плейліст відправлено! ({len(downloaded_files)} треків)\n\n📀 Бажаєш зберегти цей плейліст?",
                reply_markup=ReplyKeyboardRemove()
            )
            await message.answer(
                "Вибери опцію:",
                reply_markup=save_keyboard
            )
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


async def handle_album(message: types.Message, status_msg: types.Message, user_input: str, state: FSMContext = None, is_search: bool = False):
    """Обробка альбому зі Spotify"""
    try:
        album_url = user_input
        
        # Переходимо в стан завантаження (тільки якщо є state)
        if state:
            await state.set_state(SearchStates.downloading_album)
            await state.update_data(cancelled=False)
            
            # Показуємо кнопку скасування
            cancel_keyboard = ReplyKeyboardMarkup(
                keyboard=[[KeyboardButton(text="❌ Скасувати")]],
                resize_keyboard=True
            )
            cancel_msg = await message.answer(
                "⚠️ Завантаження розпочато...",
                reply_markup=cancel_keyboard
            )
        
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
            # Перевірка на скасування (якщо є state)
            if state:
                data = await state.get_data()
                if data.get('cancelled', False):
                    logger.info("Завантаження альбому скасовано користувачем")
                    await status_msg.edit_text("❌ Завантаження скасовано!")
                    await message.answer(
                        "🎵 Що далі?",
                        reply_markup=get_main_menu_keyboard()
                    )
                    # Видаляємо вже завантажені файли
                    for file_info in downloaded_files:
                        soundcloud.cleanup_file(file_info['path'])
                    return
            
            try:
                await status_msg.edit_text(
                    f"💿 <b>{album_info['name']}</b>\n\n"
                    f"⏳ Завантаження: {index}/{total_tracks}\n"
                    f"🎵 {track_info['name']}\n"
                    f"👤 {track_info['artists']}",
                    parse_mode=ParseMode.HTML
                )
                
                # Завантаження з SoundCloud
                user_bitrate = get_user_bitrate(message.from_user.id)
                audio_path = soundcloud.download_audio(
                    track_info['search_query'],
                    f"{track_info['artists']} - {track_info['name']}",
                    message.from_user.id,
                    user_bitrate
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
            
            # Telegram дозволяє відправляти до 10 медіа-файлів за раз
            for i in range(0, len(downloaded_files), 10):
                batch = downloaded_files[i:i+10]
                media_group = []
                
                for file_info in batch:
                    audio_file = FSInputFile(file_info['path'])
                    
                    # Не додаємо thumbnail - він не працює коректно в медіа-групах
                    # Обкладинка вже показана в окремому повідомленні вище
                    media_group.append(InputMediaAudio(
                        media=audio_file,
                        title=file_info['title'],
                        performer=file_info['performer']
                    ))
                
                # Відправляємо групу
                try:
                    await message.answer_media_group(media=media_group)
                except Exception as e:
                    logger.warning(f"Помилка при відправці медіа-групи альбому: {e}")
                    # Якщо не вдалося відправити групою, відправляємо по одному
                    for file_info in batch:
                        try:
                            audio_file = FSInputFile(file_info['path'])
                            await message.answer_audio(
                                audio=audio_file,
                                title=file_info['title'],
                                performer=file_info['performer']
                            )
                        except Exception as e2:
                            logger.error(f"Помилка при відправці файлу {file_info['title']}: {e2}")
                
                # Видаляємо файли після відправки
                for file_info in batch:
                    soundcloud.cleanup_file(file_info['path'])
            
            # Видаляємо статусне повідомлення
            await status_msg.delete()
            
            # Генеруємо унікальний ID для альбому
            album_id = hashlib.md5(f"{album_info['artist']}_{album_info['name']}".encode()).hexdigest()[:16]
            
            # Кнопка збереження альбому
            save_keyboard = InlineKeyboardMarkup(inline_keyboard=[
                [InlineKeyboardButton(
                    text="⭐ Зберегти альбом",
                    callback_data=f"save_album_{album_id}"
                )],
                [InlineKeyboardButton(text="🔙 Головне меню", callback_data="back_to_main")]
            ])
            
            # Зберігаємо інформацію про альбом
            settings = get_user_settings(message.from_user.id)
            if 'temp_items' not in settings:
                settings['temp_items'] = {}
            
            settings['temp_items'][album_id] = {
                'type': 'album',
                'name': album_info['name'],
                'artist': album_info['artist'],  # Використовуємо 'artist' (не 'artists')
                'url': user_input
            }
            
            # Показуємо меню (прибираємо Reply клавіатуру)
            await message.answer(
                f"✅ Альбом відправлено! ({len(downloaded_files)} треків)\n\n💿 Бажаєш зберегти цей альбом?",
                reply_markup=ReplyKeyboardRemove()
            )
            await message.answer(
                "Вибери опцію:",
                reply_markup=save_keyboard
            )
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
    # Завантажуємо налаштування користувачів
    load_user_settings()
    
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
        # Зберігаємо налаштування перед виходом
        save_user_settings()
        await bot.session.close()


if __name__ == "__main__":
    try:
        asyncio.run(main())
    except KeyboardInterrupt:
        logger.info("Бот зупинено користувачем")
    except Exception as e:
        logger.error(f"Критична помилка: {e}")
