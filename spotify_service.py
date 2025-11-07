import spotipy
from spotipy.oauth2 import SpotifyClientCredentials
import config
import re


class SpotifyService:
    """Клас для роботи зі Spotify"""
    
    def __init__(self):
        """Ініціалізація клієнта Spotify"""
        auth_manager = SpotifyClientCredentials(
            client_id=config.SPOTIFY_CLIENT_ID,
            client_secret=config.SPOTIFY_CLIENT_SECRET
        )
        self.spotify = spotipy.Spotify(auth_manager=auth_manager)
    
    def extract_track_id(self, url: str) -> str | None:
        """
        Витягує ID треку з Spotify URL
        
        Args:
            url: Посилання на трек Spotify
            
        Returns:
            ID треку або None
        """
        # Підтримує формати:
        # https://open.spotify.com/track/TRACK_ID
        # spotify:track:TRACK_ID
        patterns = [
            r'spotify\.com/track/([a-zA-Z0-9]+)',
            r'spotify:track:([a-zA-Z0-9]+)'
        ]
        
        for pattern in patterns:
            match = re.search(pattern, url)
            if match:
                return match.group(1)
        
        return None
    
    def get_track_info(self, track_url: str) -> dict | None:
        """
        Отримує інформацію про трек зі Spotify
        
        Args:
            track_url: Посилання на трек Spotify
            
        Returns:
            Словник з інформацією про трек або None
        """
        try:
            track_id = self.extract_track_id(track_url)
            if not track_id:
                return None
            
            track = self.spotify.track(track_id)
            
            # Формуємо інформацію про трек
            artists = ", ".join([artist['name'] for artist in track['artists']])
            
            track_info = {
                'name': track['name'],
                'artists': artists,
                'album': track['album']['name'],
                'duration_ms': track['duration_ms'],
                'preview_url': track.get('preview_url'),
                'image_url': track['album']['images'][0]['url'] if track['album']['images'] else None,
                'search_query': f"{artists} - {track['name']}"
            }
            
            return track_info
            
        except Exception as e:
            print(f"Помилка при отриманні інформації з Spotify: {e}")
            return None
    
    def search_track(self, query: str) -> dict | None:
        """
        Пошук треку на Spotify за запитом
        
        Args:
            query: Пошуковий запит
            
        Returns:
            Інформація про знайдений трек або None
        """
        try:
            results = self.spotify.search(q=query, type='track', limit=1)
            
            if not results['tracks']['items']:
                return None
            
            track = results['tracks']['items'][0]
            artists = ", ".join([artist['name'] for artist in track['artists']])
            
            track_info = {
                'name': track['name'],
                'artists': artists,
                'album': track['album']['name'],
                'duration_ms': track['duration_ms'],
                'preview_url': track.get('preview_url'),
                'image_url': track['album']['images'][0]['url'] if track['album']['images'] else None,
                'search_query': f"{artists} - {track['name']}"
            }
            
            return track_info
            
        except Exception as e:
            print(f"Помилка при пошуку треку на Spotify: {e}")
            return None
