# Sluhay Bot - Quick Start

## Проблема: "Conflict: terminated by other getUpdates request"

**Рішення:**
```powershell
# Windows
.\stop_bot.ps1

# Linux
bash stop_bot.sh
```

## Проблема: "Requested format is not available"

**Виправлено!** Бот тепер підтримує fallback формати:
- m4a → webm → будь-який аудіо → найкращий

## Проблема: "HTTP Error 403: Forbidden" (на сервері)

**Рішення:**
1. `pip install -U yt-dlp`
2. `python3 test_youtube.py` (перевірка)
3. Якщо не допомагає - додайте cookies.txt

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
