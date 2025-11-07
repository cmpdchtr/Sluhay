"""
Тестовий скрипт для перевірки роботи yt-dlp на сервері
Запустіть цей скрипт щоб перевірити чи працює завантаження з YouTube
"""
import yt_dlp

def test_download():
    """Тестове завантаження з YouTube"""
    print("🔍 Тестування завантаження з YouTube...")
    
    ydl_opts = {
        'format': 'bestaudio/best',
        'quiet': False,
        'no_warnings': False,
        'default_search': 'ytsearch1',
        'noplaylist': True,
        'extract_flat': False,
        # Важливі опції для обходу 403
        'http_headers': {
            'User-Agent': 'Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/120.0.0.0 Safari/537.36',
            'Accept': 'text/html,application/xhtml+xml,application/xml;q=0.9,*/*;q=0.8',
            'Accept-Language': 'en-us,en;q=0.5',
        },
        'extractor_args': {
            'youtube': {
                'player_client': ['android', 'web'],
                'player_skip': ['webpage', 'configs'],
            }
        },
        'source_address': '0.0.0.0',
    }
    
    try:
        with yt_dlp.YoutubeDL(ydl_opts) as ydl:
            print("\n📥 Спроба завантаження тестового відео...")
            info = ydl.extract_info("ytsearch1:test audio", download=False)
            
            if info and 'entries' in info and info['entries']:
                video = info['entries'][0]
                print(f"✅ Успішно знайдено: {video.get('title', 'Unknown')}")
                print(f"   URL: {video.get('webpage_url', 'Unknown')}")
                print(f"   Тривалість: {video.get('duration', 0)} секунд")
                
                # Перевіряємо формати
                formats = video.get('formats', [])
                audio_formats = [f for f in formats if f.get('acodec') != 'none']
                print(f"   Доступно аудіо форматів: {len(audio_formats)}")
                
                return True
            else:
                print("❌ Не вдалося знайти відео")
                return False
                
    except Exception as e:
        print(f"❌ Помилка: {e}")
        return False

if __name__ == "__main__":
    print("=" * 60)
    print("ТЕСТ yt-dlp НА СЕРВЕРІ")
    print("=" * 60)
    
    success = test_download()
    
    print("\n" + "=" * 60)
    if success:
        print("✅ Тест пройдено успішно!")
        print("Бот має працювати коректно.")
    else:
        print("❌ Тест провалено!")
        print("\nМожливі рішення:")
        print("1. Оновіть yt-dlp: pip install -U yt-dlp")
        print("2. Встановіть FFmpeg: sudo apt install ffmpeg")
        print("3. Перевірте доступ до YouTube з сервера")
        print("4. Спробуйте використати VPN або проксі")
    print("=" * 60)
