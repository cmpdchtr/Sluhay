# 🚀 Інструкція для деплою Sluhay Bot

## Швидкий старт (локально)

1. **Клонуй репозиторій**
```bash
git clone https://github.com/cmpdchtr/Sluhay.git
cd Sluhay
```

2. **Створи віртуальне середовище**
```bash
python -m venv .venv
```

3. **Активуй віртуальне середовище**
- Windows:
  ```powershell
  .\.venv\Scripts\Activate.ps1
  ```
- Linux/Mac:
  ```bash
  source .venv/bin/activate
  ```

4. **Встанови залежності**
```bash
pip install -r requirements.txt
```

5. **Налаштуй .env файл**
```bash
cp .env.example .env
```

Відкрий `.env` та заповни:
```env
TELEGRAM_BOT_TOKEN=твій_токен_від_BotFather
SPOTIFY_CLIENT_ID=твій_spotify_client_id
SPOTIFY_CLIENT_SECRET=твій_spotify_client_secret
```

### Як отримати Spotify credentials:
1. Перейди на https://developer.spotify.com/dashboard
2. Залогінься або створи акаунт
3. Натисни "Create app"
4. Заповни форму (будь-яке ім'я та опис)
5. Скопіюй Client ID та Client Secret

6. **Встанови FFmpeg**
- Windows: Завантаж з https://ffmpeg.org/download.html і додай в PATH
- Linux: `sudo apt install ffmpeg`
- Mac: `brew install ffmpeg`

7. **Запусти бота**
```bash
python main.py
```

## Деплой на сервер (Linux)

### 1. Підготовка сервера
```bash
# Оновлюємо систему
sudo apt update && sudo apt upgrade -y

# Встановлюємо Python і залежності
sudo apt install python3 python3-pip python3-venv ffmpeg -y

# Встановлюємо Git
sudo apt install git -y
```

### 2. Клонуємо проект
```bash
cd /opt
sudo git clone https://github.com/cmpdchtr/Sluhay.git
cd Sluhay
```

### 3. Налаштовуємо віртуальне середовище
```bash
sudo python3 -m venv .venv
sudo .venv/bin/pip install -r requirements.txt
```

### 4. Налаштовуємо .env
```bash
sudo cp .env.example .env
sudo nano .env
```

### 5. Створюємо systemd service
```bash
sudo nano /etc/systemd/system/sluhay-bot.service
```

Вміст файлу:
```ini
[Unit]
Description=Sluhay Telegram Bot
After=network.target

[Service]
Type=simple
User=root
WorkingDirectory=/opt/Sluhay
Environment="PATH=/opt/Sluhay/.venv/bin"
ExecStart=/opt/Sluhay/.venv/bin/python /opt/Sluhay/main.py
Restart=always
RestartSec=10

[Install]
WantedBy=multi-user.target
```

### 6. Запускаємо сервіс
```bash
sudo systemctl daemon-reload
sudo systemctl enable sluhay-bot
sudo systemctl start sluhay-bot
```

### 7. Перевірка статусу
```bash
sudo systemctl status sluhay-bot
```

### 8. Логи
```bash
# Подивитись останні логи
sudo journalctl -u sluhay-bot -n 50

# Слідкувати за логами в реальному часі
sudo journalctl -u sluhay-bot -f
```

## Корисні команди

### Зупинити бота
```bash
sudo systemctl stop sluhay-bot
```

### Перезапустити бота
```bash
sudo systemctl restart sluhay-bot
```

### Оновити код
```bash
cd /opt/Sluhay
sudo git pull
sudo systemctl restart sluhay-bot
```

### Оновити залежності
```bash
cd /opt/Sluhay
sudo .venv/bin/pip install -r requirements.txt --upgrade
sudo systemctl restart sluhay-bot
```

## Деплой на Heroku

1. **Створи Heroku app**
```bash
heroku create your-bot-name
```

2. **Додай buildpacks**
```bash
heroku buildpacks:add --index 1 https://github.com/jonathanong/heroku-buildpack-ffmpeg-latest.git
heroku buildpacks:add --index 2 heroku/python
```

3. **Встанови змінні середовища**
```bash
heroku config:set TELEGRAM_BOT_TOKEN=your_token
heroku config:set SPOTIFY_CLIENT_ID=your_client_id
heroku config:set SPOTIFY_CLIENT_SECRET=your_client_secret
```

4. **Створи Procfile**
```
worker: python main.py
```

5. **Деплой**
```bash
git push heroku main
```

6. **Запусти worker**
```bash
heroku ps:scale worker=1
```

## Моніторинг і обслуговування

### Очищення папки downloads
```bash
# Автоматичне очищення старих файлів (більше 1 дня)
find /opt/Sluhay/downloads -type f -mtime +1 -delete
```

### Додай в cron для автоочищення
```bash
sudo crontab -e
```

Додай рядок:
```
0 */6 * * * find /opt/Sluhay/downloads -type f -mtime +1 -delete
```

## Тестування

### Швидкий тест
```bash
python test_quick.py
```

### Тест бота (без запуску)
```bash
python -m py_compile main.py soundcloud_downloader.py spotify_service.py
```

## Проблеми та рішення

### Бот не відповідає
1. Перевір чи запущений: `sudo systemctl status sluhay-bot`
2. Перевір логи: `sudo journalctl -u sluhay-bot -n 50`
3. Перезапусти: `sudo systemctl restart sluhay-bot`

### Помилки завантаження
1. Перевір чи встановлений FFmpeg: `ffmpeg -version`
2. Перевір доступ до SoundCloud
3. Перевір папку downloads: `ls -la downloads/`

### Spotify не працює
1. Перевір credentials в `.env`
2. Перевір чи не заблокований API
3. Перегенеруй Client Secret на Spotify Dashboard

## Безпека

- **Ніколи** не коміть `.env` файл
- Регулярно оновлюй залежності
- Використовуй окремого користувача для бота (не root)
- Налаштуй firewall на сервері

## Підтримка

Якщо виникли проблеми:
1. Перевір логи
2. Подивись README.md
3. Створи issue на GitHub
4. Напиши @cmpdchtr
