"""
Швидкий тест SoundCloud завантаження
"""
from soundcloud_downloader import SoundCloudDownloader

def quick_test():
    """Швидкий тест"""
    downloader = SoundCloudDownloader()
    
    print("\n🧪 ШВИДКИЙ ТЕСТ SOUNDCLOUD")
    print("="*50)
    
    # Тест популярного треку
    print("\n🎵 Тестуємо: The Weeknd - Blinding Lights")
    audio_path = downloader.download_audio(
        "The Weeknd - Blinding Lights",
        "The Weeknd - Blinding Lights",
        user_id=99999
    )
    
    if audio_path:
        import os
        size_mb = os.path.getsize(audio_path) / (1024 * 1024)
        print(f"✅ Успіх! Розмір: {size_mb:.2f} МБ")
        print(f"📁 Файл: {audio_path}")
        
        # Видаляємо тестовий файл
        downloader.cleanup_file(audio_path)
        print("🗑 Файл видалено")
    else:
        print("❌ Не вдалося завантажити")
    
    print("\n" + "="*50)
    print("ТЕСТ ЗАВЕРШЕНО\n")

if __name__ == "__main__":
    quick_test()
