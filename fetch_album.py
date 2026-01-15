import json
import yt_dlp
import musicbrainzngs
import sys
from pathlib import Path

musicbrainzngs.set_useragent("AlbumVideoGenerator", "1.0", "contact@example.com")

def get_album_info(artist, album):
    print(f"🔍 Searching MusicBrainz for: {artist} - {album}")
    
    try:
        result = musicbrainzngs.search_releases(
            artist=artist,
            release=album,
            limit=5
        )
        
        if not result['release-list']:
            print("❌ Album not found in MusicBrainz")
            return None
        
        release = result['release-list'][0]
        release_id = release['id']
        
        print(f"✓ Found: {release['title']} by {release['artist-credit'][0]['artist']['name']}")
        
        release_info = musicbrainzngs.get_release_by_id(
            release_id,
            includes=['recordings', 'artist-credits']
        )
        
        tracks = []
        for medium in release_info['release']['medium-list']:
            for track in medium['track-list']:
                tracks.append({
                    'position': track['position'],
                    'title': track['recording']['title'],
                    'length': track.get('length', 'Unknown')
                })
        
        album_data = {
            'album': release['title'],
            'artist': release['artist-credit'][0]['artist']['name'],
            'release_date': release.get('date', 'Unknown'),
            'track_count': len(tracks),
            'tracks': tracks
        }
        
        print(f"✓ Found {len(tracks)} tracks")
        return album_data
        
    except Exception as e:
        print(f"❌ MusicBrainz error: {e}")
        return None

def get_youtube_urls(artist, album_data):
    print(f"\n🔍 Searching YouTube for {album_data['track_count']} tracks...")
    
    ydl_opts = {
        'quiet': True,
        'no_warnings': True,
        'extract_flat': True,
        'default_search': 'ytsearch1',
    }
    
    tracks_with_urls = []
    
    for track in album_data['tracks']:
        search_query = f"{artist} {track['title']}"
        
        try:
            with yt_dlp.YoutubeDL(ydl_opts) as ydl:
                info = ydl.extract_info(f"ytsearch1:{search_query}", download=False)
                
                if 'entries' in info and info['entries']:
                    video = info['entries'][0]
                    youtube_url = f"https://www.youtube.com/watch?v={video['id']}"
                    
                    tracks_with_urls.append({
                        'position': track['position'],
                        'title': track['title'],
                        'length': track['length'],
                        'youtube_url': youtube_url,
                        'youtube_title': video.get('title', ''),
                        'youtube_id': video['id']
                    })
                    
                    print(f"  ✓ {track['position']}. {track['title']}")
                else:
                    tracks_with_urls.append({
                        'position': track['position'],
                        'title': track['title'],
                        'length': track['length'],
                        'youtube_url': None,
                        'youtube_title': None,
                        'youtube_id': None
                    })
                    print(f"  ✗ {track['position']}. {track['title']} - Not found")
                    
        except Exception as e:
            print(f"  ✗ {track['position']}. {track['title']} - Error: {e}")
            tracks_with_urls.append({
                'position': track['position'],
                'title': track['title'],
                'length': track['length'],
                'youtube_url': None,
                'youtube_title': None,
                'youtube_id': None
            })
    
    album_data['tracks'] = tracks_with_urls
    return album_data

def save_album_data(album_data, filename=None):
    if filename is None:
        filename = f"{album_data['artist']} - {album_data['album']}.json"
    
    filename = filename.replace('/', '-').replace('\\', '-')
    
    with open(filename, 'w', encoding='utf-8') as f:
        json.dump(album_data, f, indent=2, ensure_ascii=False)
    
    print(f"\n✅ Saved to: {filename}")
    print(f"\n📊 Summary:")
    print(f"  Album: {album_data['album']}")
    print(f"  Artist: {album_data['artist']}")
    print(f"  Release: {album_data['release_date']}")
    print(f"  Tracks: {album_data['track_count']}")
    
    found = sum(1 for t in album_data['tracks'] if t['youtube_url'])
    print(f"  YouTube URLs found: {found}/{album_data['track_count']}")
    
    return filename

def fetch_album(artist, album):
    album_data = get_album_info(artist, album)
    
    if not album_data:
        return None
    
    album_data = get_youtube_urls(artist, album_data)
    filename = save_album_data(album_data)
    
    return album_data

if __name__ == "__main__":
    if len(sys.argv) == 3:
        artist = sys.argv[1]
        album = sys.argv[2]
    else:
        artist = input("Artist name: ")
        album = input("Album name: ")
    
    album_data = fetch_album(artist, album)
    
    if album_data:
        print("\n📝 Sample tracks:")
        for track in album_data['tracks'][:3]:
            print(f"\n  {track['position']}. {track['title']}")
            print(f"     YouTube: {track['youtube_url']}")
    else:
        print("❌ Failed to fetch album")
        sys.exit(1)