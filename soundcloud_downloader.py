import os
import yt_dlp
import config


class SoundCloudDownloader:
    """Клас для завантаження музики з SoundCloud"""
    
    def __init__(self):
        """Ініціалізація завантажувача"""
        self.download_dir = config.DOWNLOADS_DIR
    
    def download_audio(self, search_query: str, track_name: str, user_id: int = None) -> str | None:
        """
        Завантажує аудіо з SoundCloud за пошуковим запитом
        
        Args:
            search_query: Пошуковий запит (виконавець - назва)
            track_name: Назва треку для імені файлу
            user_id: ID користувача для унікальності файлу
            
        Returns:
            Шлях до завантаженого файлу або None
        """
        try:
            # Створюємо безпечне ім'я файлу
            safe_filename = "".join(
                c for c in track_name if c.isalnum() or c in (' ', '-', '_')
            ).rstrip()
            
            if not safe_filename:
                import time
                safe_filename = f"track_{int(time.time())}"
            
            # Додаємо user_id та timestamp для унікальності
            import time
            unique_id = f"{user_id}_{int(time.time() * 1000)}" if user_id else f"{int(time.time() * 1000)}"
            safe_filename = f"{safe_filename}_{unique_id}"
            
            output_path = os.path.join(self.download_dir, f"{safe_filename}.mp3")
            
            # Оптимізовані налаштування для SoundCloud
            ydl_opts = {
                'format': 'bestaudio/best',
                'postprocessors': [{
                    'key': 'FFmpegExtractAudio',
                    'preferredcodec': 'mp3',
                    'preferredquality': '128',
                }],
                'outtmpl': os.path.join(self.download_dir, f"{safe_filename}.%(ext)s"),
                'quiet': True,
                'no_warnings': True,
                'default_search': 'scsearch1',  # SoundCloud пошук
                'noplaylist': True,
                'no_check_certificate': True,
                'geo_bypass': True,
                # Швидкісні налаштування
                'retries': 2,
                'fragment_retries': 2,
                'skip_unavailable_fragments': True,
                'concurrent_fragment_downloads': 16,
                'http_chunk_size': 1048576,  # 1MB chunks
                'buffersize': 1024 * 16,
                'throttled_rate': None,
                'http_headers': {
                    'User-Agent': 'Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36',
                },
                # Пропускаємо зайві дані
                'writethumbnail': False,
                'writesubtitles': False,
                'writeautomaticsub': False,
            }
            
            # Завантажуємо з SoundCloud
            with yt_dlp.YoutubeDL(ydl_opts) as ydl:
                ydl.download([search_query])
            
            # Перевіряємо чи файл створено
            if os.path.exists(output_path):
                print(f"✓ Завантажено з SoundCloud: {track_name}")
                return output_path
            else:
                # Шукаємо файл в папці downloads
                print(f"Очікуваний файл не знайдено: {output_path}")
                print(f"Пошук файлів в {self.download_dir}...")
                
                import time
                current_time = time.time()
                for file in os.listdir(self.download_dir):
                    if file.endswith('.mp3'):
                        file_path = os.path.join(self.download_dir, file)
                        # Файл створено недавно (менше 60 секунд тому)
                        if current_time - os.path.getmtime(file_path) < 60:
                            print(f"Знайдено файл: {file_path}")
                            try:
                                os.rename(file_path, output_path)
                                return output_path
                            except:
                                return file_path
                
                print(f"✗ MP3 файл не знайдено в {self.download_dir}")
                return None
                
        except Exception as e:
            print(f"❌ Помилка при завантаженні з SoundCloud: {e}")
            import traceback
            traceback.print_exc()
            return None
    
    def cleanup_file(self, filepath: str) -> None:
        """
        Видаляє файл після відправки
        
        Args:
            filepath: Шлях до файлу для видалення
        """
        try:
            if os.path.exists(filepath):
                os.remove(filepath)
                print(f"Файл видалено: {filepath}")
        except Exception as e:
            print(f"Не вдалося видалити файл {filepath}: {e}")
