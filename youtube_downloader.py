import os
import yt_dlp
import config


class YouTubeDownloader:
    """Клас для завантаження музики з YouTube"""
    
    def __init__(self):
        """Ініціалізація завантажувача"""
        self.download_dir = config.DOWNLOADS_DIR
    
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
            
            # Налаштування для yt-dlp
            ydl_opts = {
                'format': 'bestaudio/best',
                'postprocessors': [{
                    'key': 'FFmpegExtractAudio',
                    'preferredcodec': 'mp3',
                    'preferredquality': '192',
                }],
                'outtmpl': os.path.join(self.download_dir, f"{safe_filename}.%(ext)s"),
                'quiet': True,
                'no_warnings': True,
                'default_search': 'ytsearch1',  # Пошук на YouTube, перший результат
                'noplaylist': True,
                'extract_flat': False,
                'ignoreerrors': False,
                'no_check_certificate': True,
                'prefer_insecure': True,
                'geo_bypass': True,
                'age_limit': None,
                # Додаткові опції для обходу обмежень
                'extractor_args': {
                    'youtube': {
                        'skip': ['hls', 'dash', 'translated_subs'],
                        'player_skip': ['configs', 'webpage'],
                        'player_client': ['android', 'web'],
                    }
                },
            }
            
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
