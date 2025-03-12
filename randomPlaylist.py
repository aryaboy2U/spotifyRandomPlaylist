import spotipy
import string
from spotipy.oauth2 import SpotifyOAuth
import json
from random import randint
import random
import datetime
import itertools
import os.path
import os

# Importing variables - keeping config import pattern
from config.config import username
from config.config import mainPlaylist
from config.config import dislikedPlaylist
from config.config import recentPlaylist
from config.config import favPlaylists
from config.config import SPOTIPY_CLIENT_ID
from config.config import SPOTIPY_CLIENT_SECRET
from config.config import SPOTIPY_REDIRECT_URI

# Setting scope for Spotify API
scope = ('playlist-modify-public','playlist-read-collaborative','user-library-read',
         'playlist-modify-private','playlist-modify-private','user-read-recently-played')
cutoffDate = datetime.datetime.today() - datetime.timedelta(days=10)

# Determine cache path dynamically - use current directory
cache_path = f"./.cache-{username}"
print(f"Using cache file: {cache_path}")

# Initialize Spotify OAuth handler for headless operation
def get_spotify_client():
    # Check if the cache file exists
    if os.path.isfile(cache_path):
        # If cache exists, use it directly
        print(f"Found existing cache file at {cache_path}")
        token = SpotifyOAuth(
            client_id=SPOTIPY_CLIENT_ID,
            client_secret=SPOTIPY_CLIENT_SECRET,
            redirect_uri=SPOTIPY_REDIRECT_URI,
            scope=scope,
            cache_path=cache_path,
            username=username,
            open_browser=False  # Prevent browser opening
        )
        return spotipy.Spotify(auth_manager=token)
    else:
        print(f"No cache file found. First-time authorization required.")
        # For first-time setup, generate the URL and prompt for the redirect URL
        auth_manager = SpotifyOAuth(
            client_id=SPOTIPY_CLIENT_ID,
            client_secret=SPOTIPY_CLIENT_SECRET,
            redirect_uri=SPOTIPY_REDIRECT_URI,
            scope=scope,
            cache_path=cache_path,
            username=username,
            open_browser=False  # Prevent browser opening
        )
        
        # Get the authorization URL
        auth_url = auth_manager.get_authorize_url()
        print(f"Please go to this URL and authorize the app: {auth_url}")
        
        # Get the response URL after authorization
        response = input("Enter the URL you were redirected to: ")
        
        # Get and cache the token
        code = auth_manager.parse_response_code(response)
        auth_manager.get_access_token(code)
        
        return spotipy.Spotify(auth_manager=auth_manager)

# Get Spotify client
try:
    print("Initializing Spotify client...")
    spotifyObject = get_spotify_client()
    print("Authorization successful!")
except Exception as e:
    print(f"Error during authorization: {e}")
    exit(1)

# Function that gets all tracks in a playlist
def get_playlist_tracks(username, playlist_id):
    results = spotifyObject.user_playlist_tracks(username, playlist_id)
    tracks = results['items']
    while results['next']:
        results = spotifyObject.next(results)
        tracks.extend(results['items'])
    return tracks

# Getting list of disliked Songs
print(f"Fetching disliked songs from playlist: {dislikedPlaylist}")
results = spotifyObject.user_playlist_tracks(username, dislikedPlaylist)
dislength = (len(results['items']))
disliked = []
for item in results['items']:
    track = item['track']
    disliked.append(track['uri'])
print(f"Found {len(disliked)} disliked tracks")

# Loading recently played songs from playlist recentlyPlayed
print(f"Fetching recently played songs from playlist: {recentPlaylist}")
recentlyPlayedTracks = []
recentlyPlayedPlaylist = get_playlist_tracks(username, recentPlaylist)
for item in recentlyPlayedPlaylist:
    track = item['track']
    date = item['added_at']
    date_time_obj = datetime.datetime.strptime(date, '%Y-%m-%dT%H:%M:%SZ')
    if date_time_obj.date() >= cutoffDate.date():  # filtering out songs that have been played within cutoff period
        recentlyPlayedTracks.append(track['uri'])

print(f"Found {len(recentlyPlayedTracks)} recently played tracks within the last {(datetime.datetime.today() - cutoffDate).days} days")

# Updating recentlyPlayed playlist with new recentlyPlayed
print("Fetching user's most recently played tracks from Spotify...")
newRecentlyPlayedexcluded = []
newRecentlyPlayed = spotifyObject.current_user_recently_played()
for item in newRecentlyPlayed['items']:
    date = item['played_at']
    track = item['track']
    if track['uri'] not in recentlyPlayedTracks:
        newRecentlyPlayedexcluded.append(track['uri'])

print(f"Found {len(newRecentlyPlayedexcluded)} new recently played tracks")

if len(newRecentlyPlayedexcluded) > 0:
    print(f"Adding {len(newRecentlyPlayedexcluded)} new tracks to recent playlist")
    spotifyObject.user_playlist_add_tracks(user=username, playlist_id=recentPlaylist, tracks=newRecentlyPlayedexcluded)
    print("Recently played playlist updated")

list_of_songs = []

# Function that populates list_of_songs with songs from other favPlaylists
def fillPlaylist(playlist_id, count):
    # Getting size of the playlist for the random range numbers
    print(f"Fetching tracks from playlist: {playlist_id}")
    library = get_playlist_tracks(username, playlist_id)
    length = len(library)
    var = int(count)  # converting to int
    
    added_count = 0
    # The number in range is the number of songs that you want in your playlist
    for a in range(var):
        if length == 0:
            print(f"Playlist {playlist_id} is empty, skipping")
            return 0
            
        ran = randint(0, length - 1)
        track = library[ran]['track']
        
        # Check valid uri, and excludes duplicates, disliked songs, and recently played songs
        if (track['uri'] not in list_of_songs and 
            track['uri'] not in disliked and 
            track['uri'] not in recentlyPlayedTracks and 
            track['uri'] not in newRecentlyPlayedexcluded and 
            len(track['uri']) == 36):
            list_of_songs.append(track['uri'])
            added_count += 1
        else:
            print(f"Discarded: {track['name']}")
    
    print(f"Added {added_count} tracks from playlist {playlist_id}")
    return added_count

# Randomly selecting favorite playlists and grabbing random number of songs from each
print(f"Starting to fill main playlist from {len(favPlaylists)} favorite playlists")
random.shuffle(favPlaylists)
list_cycle = itertools.cycle(favPlaylists)

target_count = 90  # Spotify has a 100 songs limit that you can populate per call
retry_count = 0
max_retries = 10

while len(list_of_songs) < target_count and retry_count < max_retries:
    ran = randint(1, 10)
    next_item = next(list_cycle)
    added = fillPlaylist(next_item, ran)  # Calling fillPlaylist function to select random songs
    print(f"Current song count: {len(list_of_songs)} / {target_count}")
    
    if added == 0:
        retry_count += 1

if len(list_of_songs) < target_count:
    print(f"Warning: Could only find {len(list_of_songs)} tracks, which is less than the target of {target_count}")

# Shuffling playlist
print("Shuffling selected tracks")
random.shuffle(list_of_songs)

# Clearing main playlist
print(f"Clearing main playlist: {mainPlaylist}")
results = spotifyObject.user_playlist_tracks(username, mainPlaylist)
list_removed = []
for item in results['items']:
    track = item['track']
    list_removed.append(track['uri'])

if list_removed:
    print(f"Removing {len(list_removed)} tracks from main playlist")
    spotifyObject.user_playlist_remove_all_occurrences_of_tracks(username, mainPlaylist, list_removed)
    print("Main playlist cleared")
else:
    print("Main playlist is already empty")

# Populating playlist
print(f"Adding {len(list_of_songs)} tracks to main playlist")
spotifyObject.user_playlist_add_tracks(user=username, playlist_id=mainPlaylist, tracks=list_of_songs)
print('Playlist has been populated successfully!')

