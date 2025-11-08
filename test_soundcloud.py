"""
Тестовий скрипт для перевірки SoundCloud інтеграції
"""
from youtube_downloader import YouTubeDownloader
import os

def test_download():
    """Тестуємо завантаження з різних джерел"""
    downloader = YouTubeDownloader()
    
    # Тест 1: Популярний трек (має бути на SoundCloud)
    print("\n" + "="*50)
    print("ТЕСТ 1: Популярний трек")
    print("="*50)
    audio_path, source = downloader.download_audio_smart(
        "The Weeknd - Blinding Lights",
        "The Weeknd - Blinding Lights",
        user_id=12345
    )
    
    if audio_path:
        print(f"✅ Завантажено з {source.upper()}")
        print(f"📁 Файл: {audio_path}")
        size_mb = os.path.getsize(audio_path) / (1024 * 1024)
        print(f"📦 Розмір: {size_mb:.2f} МБ")
        downloader.cleanup_file(audio_path)
        print("🗑 Файл видалено")
    else:
        print("❌ Не вдалося завантажити")
    
    # Тест 2: Рідкісний/український трек (може бути тільки на YouTube)
    print("\n" + "="*50)
    print("ТЕСТ 2: Український трек")
    print("="*50)
    audio_path, source = downloader.download_audio_smart(
        "Скрябін - Люди як кораблі",
        "Скрябін - Люди як кораблі",
        user_id=12345
    )
    
    if audio_path:
        print(f"✅ Завантажено з {source.upper()}")
        print(f"📁 Файл: {audio_path}")
        size_mb = os.path.getsize(audio_path) / (1024 * 1024)
        print(f"📦 Розмір: {size_mb:.2f} МБ")
        downloader.cleanup_file(audio_path)
        print("🗑 Файл видалено")
    else:
        print("❌ Не вдалося завантажити")
    
    print("\n" + "="*50)
    print("ТЕСТУВАННЯ ЗАВЕРШЕНО")
    print("="*50)

if __name__ == "__main__":
    test_download()
