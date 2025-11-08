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
            
            # МАКСИМАЛЬНА ШВИДКІСТЬ - обмежуємо якість для маленьких файлів
            ydl_opts = {
                # Обмежуємо бітрейт для швидкості - менший бітрейт = менший файл = швидше
                'format': (
                    'bestaudio[abr<=96]/'      # Спочатку до 96kbps (дуже швидко)
                    'bestaudio[abr<=128]/'     # Потім до 128kbps (швидко)
                    'bestaudio[abr<=160]/'     # До 160kbps (нормально)
                    'bestaudio'                 # Будь-яке аудіо
                ),
                'postprocessors': [{
                    'key': 'FFmpegExtractAudio',
                    'preferredcodec': 'mp3',
                    'preferredquality': '128',
                }],
                'outtmpl': os.path.join(self.download_dir, f"{safe_filename}.%(ext)s"),
                'quiet': True,
                'no_warnings': True,
                'default_search': 'ytsearch1',
                'noplaylist': True,
                'no_check_certificate': True,
                'geo_bypass': True,
                'retries': 2,  # Зменшено до 2 для швидшої відмови
                'fragment_retries': 2,
                'skip_unavailable_fragments': True,
                'ignore_no_formats_error': True,
                # Агресивні оптимізації швидкості
                'concurrent_fragment_downloads': 8,  # Ще більше паралельних завантажень
                'buffer_size': 1024 * 256,  # Великий буфер - 256KB
                'http_chunk_size': 1024 * 1024 * 5,  # 5MB chunks
                'extractor_retries': 1,  # Тільки 1 спроба для extractor
                'file_access_retries': 2,
                'throttled_rate': None,
                'http_headers': {
                    'User-Agent': 'Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36',
                    'Accept': '*/*',
                    'Accept-Encoding': 'gzip, deflate',
                    'Connection': 'keep-alive',
                },
                'extractor_args': {
                    'youtube': {
                        'player_client': ['android'],  # Тільки android - він найшвидший
                        'player_skip': ['webpage', 'configs', 'js'],  # Пропускаємо все зайве
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
