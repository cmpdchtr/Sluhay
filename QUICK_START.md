# Sluhay Bot - Quick Start

## ⚠️ ВАЖЛИВА ІНФОРМАЦІЯ ПРО COOKIES

**НЕ створюйте файл cookies.txt без необхідності!**

Старі/невалідні cookies ВИКЛИКАЮТЬ ПОМИЛКИ:
- "Requested format is not available"
- "HTTP Error 403: Forbidden"

**Якщо бот не працює - ВИДАЛІТЬ cookies.txt (якщо він є)**

## Проблема: "Conflict: terminated by other getUpdates request"

**Рішення:**
```powershell
# Windows
.\stop_bot.ps1

# Linux
bash stop_bot.sh
```

## Проблема: "Requested format is not available"

**Найчастіша причина:** старий файл cookies.txt

**Рішення:**
1. Видаліть cookies.txt (якщо є)
2. Оновіть yt-dlp: `pip install -U yt-dlp`
3. Перезапустіть бота

## Проблема: "HTTP Error 403: Forbidden" (на сервері)

**Рішення:**
1. `pip install -U yt-dlp`
2. Видаліть cookies.txt (якщо є)
3. `python3 test_youtube.py` (перевірка)
4. Тільки якщо НЕ допомагає - додайте СВІЖІ cookies.txt

## Запуск

**Windows:**
```powershell
python main.py
```

**Linux:**
```bash
python3 main.py

# У фоні:
nohup python3 main.py > bot.log 2>&1 &
```

## Файли

- `main.py` - основний бот
- `config.py` - конфігурація
- `spotify_service.py` - Spotify API
- `youtube_downloader.py` - YouTube завантаження
- `.env` - токени (створи сам!)
- `stop_bot.ps1` / `stop_bot.sh` - зупинка бота
- `test_youtube.py` - тест YouTube
- `setup_server.sh` - автоналаштування Linux
