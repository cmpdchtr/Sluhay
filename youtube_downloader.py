import os
import yt_dlp
import config


class YouTubeDownloader:
    """Клас для завантаження музики з YouTube"""
    
    def __init__(self):
        """Ініціалізація завантажувача"""
        self.download_dir = config.DOWNLOADS_DIR
        # COOKIES ВИМКНЕНО! Вони викликають проблеми з форматами YouTube.
        # Бот працює КРАЩЕ без них!
        self.cookies_file = None
    
    def download_audio(self, search_query: str, track_name: str, user_id: int = None) -> str | None:
        """
        Завантажує аудіо з YouTube за пошуковим запитом
        
        Args:
            search_query: Пошуковий запит (виконавець - назва)
            track_name: Назва треку для імені файлу
            user_id: ID користувача для унікальності файлу (опціонально)
            
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
            
            # Простий та НАДІЙНИЙ підхід з якістю 96kbps для ШВИДКОСТІ
            ydl_opts = {
                # Простий формат який точно спрацює
                'format': 'bestaudio/best',
                'postprocessors': [{
                    'key': 'FFmpegExtractAudio',
                    'preferredcodec': 'mp3',
                    'preferredquality': '96',  # 96kbps для швидшої конвертації та менших файлів
                }],
                'outtmpl': os.path.join(self.download_dir, f"{safe_filename}.%(ext)s"),
                'quiet': True,
                'no_warnings': True,
                'default_search': 'ytsearch1',
                'noplaylist': True,
                'no_check_certificate': True,
                'geo_bypass': True,
                'retries': 3,
                'fragment_retries': 3,
                'skip_unavailable_fragments': True,
                'ignore_no_formats_error': True,
                # Максимальні оптимізації швидкості
                'concurrent_fragment_downloads': 10,  # Максимум паралельних завантажень
                'http_chunk_size': 10485760,  # 10MB chunks для швидшого завантаження
                'throttled_rate': None,
                'http_headers': {
                    'User-Agent': 'Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36',
                },
                'extractor_args': {
                    'youtube': {
                        'player_client': ['android'],
                        'player_skip': ['webpage'],
                    }
                },
            }
            
            # Cookies ВИМКНЕНО - вони викликають помилки!
            # Бот працює стабільніше БЕЗ cookies
            
            # Завантажуємо аудіо
            with yt_dlp.YoutubeDL(ydl_opts) as ydl:
                ydl.download([search_query])
            
            # Перевіряємо, чи файл створено
            if os.path.exists(output_path):
                return output_path
            else:
                # Шукаємо файл в папці downloads
                print(f"Очікуваний файл не знайдено: {output_path}")
                print(f"Пошук файлів в {self.download_dir}...")
                
                # Шукаємо будь-який .mp3 файл, створений щойно
                import time
                current_time = time.time()
                for file in os.listdir(self.download_dir):
                    if file.endswith('.mp3'):
                        file_path = os.path.join(self.download_dir, file)
                        # Перевіряємо, чи файл створено недавно (менше 60 секунд тому)
                        if current_time - os.path.getmtime(file_path) < 60:
                            print(f"Знайдено файл: {file_path}")
                            # Перейменовуємо файл на очікуване ім'я
                            try:
                                os.rename(file_path, output_path)
                                return output_path
                            except:
                                # Якщо не вдалося перейменувати, повертаємо оригінальний шлях
                                return file_path
                
                print(f"MP3 файл не знайдено в {self.download_dir}")
                return None
                
        except Exception as e:
            print(f"Помилка при завантаженні з YouTube: {e}")
            import traceback
            traceback.print_exc()
            return None
    
    def download_from_soundcloud(self, search_query: str, track_name: str, user_id: int = None) -> str | None:
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
            
            # Налаштування для SoundCloud - швидкі та прості
            ydl_opts = {
                'format': 'bestaudio/best',
                'postprocessors': [{
                    'key': 'FFmpegExtractAudio',
                    'preferredcodec': 'mp3',
                    'preferredquality': '96',
                }],
                'outtmpl': os.path.join(self.download_dir, f"{safe_filename}.%(ext)s"),
                'quiet': True,
                'no_warnings': True,
                'default_search': 'scsearch1',  # SoundCloud search!
                'noplaylist': True,
                'retries': 2,  # Менше спроб для швидкості
                'fragment_retries': 2,
                'http_chunk_size': 10485760,
                'concurrent_fragment_downloads': 10,
            }
            
            # Завантажуємо з SoundCloud
            with yt_dlp.YoutubeDL(ydl_opts) as ydl:
                ydl.download([search_query])
            
            # Перевіряємо файл
            if os.path.exists(output_path):
                print(f"✓ Завантажено з SoundCloud: {track_name}")
                return output_path
            else:
                print(f"✗ Файл не знайдено на SoundCloud: {track_name}")
                return None
                
        except Exception as e:
            print(f"SoundCloud помилка: {e}")
            return None
    
    def download_audio_smart(self, search_query: str, track_name: str, user_id: int = None) -> tuple[str | None, str]:
        """
        Розумне завантаження: спочатку SoundCloud, потім YouTube
        
        Args:
            search_query: Пошуковий запит
            track_name: Назва треку
            user_id: ID користувача
            
        Returns:
            Tuple (шлях до файлу, джерело: 'soundcloud' або 'youtube')
        """
        # Спочатку пробуємо SoundCloud (швидше)
        print(f"🔍 Шукаю на SoundCloud: {search_query}")
        soundcloud_path = self.download_from_soundcloud(search_query, track_name, user_id)
        
        if soundcloud_path:
            return soundcloud_path, 'soundcloud'
        
        # Якщо не знайшли на SoundCloud, йдемо на YouTube
        print(f"🔍 Шукаю на YouTube: {search_query}")
        youtube_path = self.download_audio(search_query, track_name, user_id)
        
        if youtube_path:
            return youtube_path, 'youtube'
        
        return None, 'none'
    
    def cleanup_file(self, filepath: str) -> None:
        """
        Видаляє файл після відправки
        
        Args:
            filepath: Шлях до файлу
        """
        try:
            if os.path.exists(filepath):
                os.remove(filepath)
                print(f"Файл видалено: {filepath}")
        except Exception as e:
            print(f"Помилка при видаленні файлу: {e}")
    
    def get_video_info(self, search_query: str) -> dict | None:
        """
        Отримує інформацію про відео без завантаження
        
        Args:
            search_query: Пошуковий запит
            
        Returns:
            Інформація про відео або None
        """
        try:
            ydl_opts = {
                'quiet': True,
                'no_warnings': True,
                'default_search': 'ytsearch1',
                'noplaylist': True,
            }
            
            with yt_dlp.YoutubeDL(ydl_opts) as ydl:
                info = ydl.extract_info(search_query, download=False)
                
                if 'entries' in info:
                    # Це результат пошуку
                    video = info['entries'][0]
                else:
                    video = info
                
                return {
                    'title': video.get('title'),
                    'duration': video.get('duration'),
                    'url': video.get('webpage_url'),
                    'thumbnail': video.get('thumbnail')
                }
                
        except Exception as e:
            print(f"Помилка при отриманні інформації з YouTube: {e}")
            return None
