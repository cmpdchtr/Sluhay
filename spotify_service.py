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
    
    def extract_playlist_id(self, url: str) -> str | None:
        """
        Витягує ID плейлиста з Spotify URL
        
        Args:
            url: Посилання на плейлист Spotify
            
        Returns:
            ID плейлиста або None
        """
        patterns = [
            r'spotify\.com/playlist/([a-zA-Z0-9]+)',
            r'spotify:playlist:([a-zA-Z0-9]+)'
        ]
        
        for pattern in patterns:
            match = re.search(pattern, url)
            if match:
                return match.group(1)
        
        return None
    
    def extract_album_id(self, url: str) -> str | None:
        """
        Витягує ID альбому з Spotify URL
        
        Args:
            url: Посилання на альбом Spotify
            
        Returns:
            ID альбому або None
        """
        patterns = [
            r'spotify\.com/album/([a-zA-Z0-9]+)',
            r'spotify:album:([a-zA-Z0-9]+)'
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
    
    def search_album(self, query: str) -> dict | None:
        """
        Пошук альбому на Spotify за запитом
        
        Args:
            query: Пошуковий запит
            
        Returns:
            Інформація про знайдений альбом (ID у форматі URL) або None
        """
        try:
            results = self.spotify.search(q=query, type='album', limit=1)
            
            if not results['albums']['items']:
                return None
            
            album = results['albums']['items'][0]
            # Повертаємо URL альбому, щоб потім використати get_album_info
            album_url = f"https://open.spotify.com/album/{album['id']}"
            
            return {'url': album_url}
            
        except Exception as e:
            print(f"Помилка при пошуку альбому на Spotify: {e}")
            return None
    
    def search_playlist(self, query: str) -> dict | None:
        """
        Пошук плейлиста на Spotify за запитом
        
        Args:
            query: Пошуковий запит
            
        Returns:
            Інформація про знайдений плейлист (ID у форматі URL) або None
        """
        try:
            results = self.spotify.search(q=query, type='playlist', limit=1)
            
            if not results['playlists']['items']:
                return None
            
            playlist = results['playlists']['items'][0]
            # Повертаємо URL плейлиста, щоб потім використати get_playlist_info
            playlist_url = f"https://open.spotify.com/playlist/{playlist['id']}"
            
            return {'url': playlist_url}
            
        except Exception as e:
            print(f"Помилка при пошуку плейлиста на Spotify: {e}")
            return None
    
    def get_playlist_info(self, playlist_url: str) -> dict | None:
        """
        Отримує інформацію про плейлист зі Spotify
        
        Args:
            playlist_url: Посилання на плейлист Spotify
            
        Returns:
            Словник з інформацією про плейлист та список треків
        """
        try:
            playlist_id = self.extract_playlist_id(playlist_url)
            if not playlist_id:
                return None
            
            playlist = self.spotify.playlist(playlist_id)
            
            tracks = []
            for item in playlist['tracks']['items']:
                if item['track']:
                    track = item['track']
                    artists = ", ".join([artist['name'] for artist in track['artists']])
                    tracks.append({
                        'name': track['name'],
                        'artists': artists,
                        'album': track['album']['name'],
                        'duration_ms': track['duration_ms'],
                        'search_query': f"{artists} - {track['name']}"
                    })
            
            playlist_info = {
                'name': playlist['name'],
                'description': playlist.get('description', ''),
                'owner': playlist['owner']['display_name'],
                'total_tracks': len(tracks),
                'image_url': playlist['images'][0]['url'] if playlist['images'] else None,
                'tracks': tracks
            }
            
            return playlist_info
            
        except Exception as e:
            print(f"Помилка при отриманні плейлиста з Spotify: {e}")
            return None
    
    def get_album_info(self, album_url: str) -> dict | None:
        """
        Отримує інформацію про альбом зі Spotify
        
        Args:
            album_url: Посилання на альбом Spotify
            
        Returns:
            Словник з інформацією про альбом та список треків
        """
        try:
            album_id = self.extract_album_id(album_url)
            if not album_id:
                return None
            
            album = self.spotify.album(album_id)
            
            tracks = []
            for track in album['tracks']['items']:
                artists = ", ".join([artist['name'] for artist in track['artists']])
                tracks.append({
                    'name': track['name'],
                    'artists': artists,
                    'album': album['name'],
                    'duration_ms': track['duration_ms'],
                    'search_query': f"{artists} - {track['name']}"
                })
            
            album_info = {
                'name': album['name'],
                'artist': ", ".join([artist['name'] for artist in album['artists']]),
                'release_date': album.get('release_date', ''),
                'total_tracks': len(tracks),
                'image_url': album['images'][0]['url'] if album['images'] else None,
                'tracks': tracks
            }
            
            return album_info
            
        except Exception as e:
            print(f"Помилка при отриманні альбому з Spotify: {e}")
            return None
