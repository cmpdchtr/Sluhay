import os
import yt_dlp
import config


class YouTubeDownloader:
    """Клас для завантаження музики з YouTube"""
    
    def __init__(self):
        """Ініціалізація завантажувача"""
        self.download_dir = config.DOWNLOADS_DIR
        # Перевіряємо чи є файл з cookies (для обходу блокувань YouTube)
        self.cookies_file = os.path.join(os.path.dirname(__file__), 'cookies.txt')
        if not os.path.exists(self.cookies_file):
            self.cookies_file = None
    
    def download_audio(self, search_query: str, track_name: str) -> str | None:
        """
        Завантажує аудіо з YouTube за пошуковим запитом
        
        Args:
            search_query: Пошуковий запит (виконавець - назва)
            track_name: Назва треку для імені файлу
            
        Returns:
            Шлях до завантаженого файлу або None
        """
        try:
            # Створюємо безпечне ім'я файлу (видаляємо всі спецсимволи окрім алфавітно-цифрових, пробілів, дефісів та підкреслень)
            safe_filename = "".join(
                c for c in track_name if c.isalnum() or c in (' ', '-', '_')
            ).rstrip()
            
            # Якщо після очищення файл порожній, використовуємо timestamp
            if not safe_filename:
                import time
                safe_filename = f"track_{int(time.time())}"
            
            output_path = os.path.join(self.download_dir, f"{safe_filename}.mp3")
            
            # Налаштування для yt-dlp з обходом блокувань
            ydl_opts = {
                # Використовуємо більш гнучкий формат з fallback опціями
                'format': 'bestaudio[ext=m4a]/bestaudio[ext=webm]/bestaudio/best',
                'postprocessors': [{
                    'key': 'FFmpegExtractAudio',
                    'preferredcodec': 'mp3',
                    'preferredquality': '192',
                }],
                'outtmpl': os.path.join(self.download_dir, f"{safe_filename}.%(ext)s"),
                'quiet': True,
                'no_warnings': True,
                'default_search': 'ytsearch1',
                'noplaylist': True,
                'extract_flat': False,
                'ignoreerrors': False,
                'no_check_certificate': True,
                'geo_bypass': True,
                'age_limit': None,
                # Додаємо retry і fragment опції
                'retries': 10,
                'fragment_retries': 10,
                'skip_unavailable_fragments': True,
                # Важливі опції для обходу 403 помилки
                'http_headers': {
                    'User-Agent': 'Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/120.0.0.0 Safari/537.36',
                    'Accept': 'text/html,application/xhtml+xml,application/xml;q=0.9,*/*;q=0.8',
                    'Accept-Language': 'en-us,en;q=0.5',
                    'Accept-Encoding': 'gzip,deflate',
                    'Accept-Charset': 'ISO-8859-1,utf-8;q=0.7,*;q=0.7',
                },
                # Додаткові опції для обходу обмежень YouTube
                'extractor_args': {
                    'youtube': {
                        'player_client': ['android', 'web'],
                        'player_skip': ['webpage', 'configs'],
                        'skip': ['hls', 'dash'],
                    }
                },
                # Використовуємо IPv4 (деякі сервери мають проблеми з IPv6)
                'source_address': '0.0.0.0',
            }
            
            # Якщо є файл cookies - використовуємо його
            if self.cookies_file:
                ydl_opts['cookiefile'] = self.cookies_file
            
            # Завантажуємо аудіо
            with yt_dlp.YoutubeDL(ydl_opts) as ydl:
                info = ydl.extract_info(search_query, download=True)
                
                # Перевіряємо, чи є аудіо в результаті
                if info and 'entries' in info:
                    video_info = info['entries'][0] if info['entries'] else None
                else:
                    video_info = info
                
                # Якщо відео не має аудіо форматів
                if video_info and 'formats' in video_info:
                    has_audio = any(
                        f.get('acodec') != 'none' and f.get('acodec') is not None 
                        for f in video_info.get('formats', [])
                    )
                    if not has_audio:
                        print("Відео не містить аудіо доріжки")
                        return None
            
            # Перевіряємо, чи файл створено
            if os.path.exists(output_path):
                return output_path
            else:
                # Шукаємо файл в папці downloads
                print(f"Очікуваний файл не знайдено: {output_path}")
                print(f"Пошук файлів в {self.download_dir}...")
                
                # Шукаємо будь-який .mp3 файл, створений щойно
                for file in os.listdir(self.download_dir):
                    if file.endswith('.mp3'):
                        file_path = os.path.join(self.download_dir, file)
                        # Перевіряємо, чи файл створено недавно (менше 60 секунд тому)
                        if os.path.getmtime(file_path) > (os.path.getctime(self.download_dir) if os.path.exists(self.download_dir) else 0):
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
