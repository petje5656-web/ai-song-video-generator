import json
import os
import sys
import subprocess
from pathlib import Path

class AlbumPipeline:
    def __init__(self, album_json_path: str):
        with open(album_json_path, 'r') as f:
            self.album_data = json.load(f)
        
        self.progress_file = 'album_progress.json'
        self.load_progress()
    
    def load_progress(self):
        if os.path.exists(self.progress_file):
            with open(self.progress_file, 'r') as f:
                self.progress = json.load(f)
        else:
            self.progress = {
                'album': self.album_data['album'],
                'artist': self.album_data['artist'],
                'total_tracks': self.album_data['track_count'],
                'completed_tracks': [],
                'failed_tracks': [],
                'current_track_index': 0,
                'current_track': None,
                'status': 'pending'
            }
            self.save_progress()
    
    def save_progress(self):
        with open(self.progress_file, 'w') as f:
            json.dump(self.progress, f, indent=2)
    
    def get_next_track(self):
        tracks = self.album_data['tracks']
        
        while self.progress['current_track_index'] < len(tracks):
            track = tracks[self.progress['current_track_index']]
            track_id = f"{track['position']}_{track['title']}"
            
            if track_id not in self.progress['completed_tracks'] and \
               track_id not in self.progress['failed_tracks']:
                self.progress['current_track'] = track
                self.save_progress()
                return track
            
            self.progress['current_track_index'] += 1
        
        return None
    
    def mark_completed(self, track, video_path):
        track_id = f"{track['position']}_{track['title']}"
        self.progress['completed_tracks'].append({
            'track_id': track_id,
            'title': track['title'],
            'position': track['position'],
            'video_path': video_path
        })
        self.progress['current_track_index'] += 1
        self.save_progress()
    
    def mark_failed(self, track, error):
        track_id = f"{track['position']}_{track['title']}"
        self.progress['failed_tracks'].append({
            'track_id': track_id,
            'title': track['title'],
            'position': track['position'],
            'error': str(error)
        })
        self.progress['current_track_index'] += 1
        self.save_progress()
    
    def is_complete(self):
        total = self.album_data['track_count']
        processed = len(self.progress['completed_tracks']) + len(self.progress['failed_tracks'])
        return processed >= total
    
    def generate_track(self, track):
        print(f"\n{'='*60}")
        print(f"🎵 Processing Track {track['position']}/{self.album_data['track_count']}")
        print(f"   {track['title']}")
        print(f"{'='*60}\n")
        
        try:
            print("Step 1: Fetching lyrics...")
            result = subprocess.run([
                'python', 'fetch_lyrics.py',
                track['title'],
                self.album_data['artist'],
                track.get('youtube_url', '')
            ], check=True, capture_output=True, text=True)
            print(result.stdout)
            
            print("\nStep 2: Generating AI song...")
            result = subprocess.run([
                'python', 'generate_song.py'
            ], check=True, capture_output=True, text=True)
            print(result.stdout)
            
            print("\nStep 3: Creating music video...")
            result = subprocess.run([
                'python', 'create_video.py'
            ], check=True, capture_output=True, text=True)
            print(result.stdout)
            
            video_filename = f"{track['title'].replace(' ', '_').lower()}_lofi_music_video.mp4"
            video_path = os.path.join('outputs', video_filename)
            
            if os.path.exists(video_path):
                self.mark_completed(track, video_path)
                print(f"\n✅ Track {track['position']} completed!")
                return True
            else:
                raise Exception("Video file not created")
                
        except subprocess.CalledProcessError as e:
            print(f"\n❌ Error: {e}")
            print(f"stderr: {e.stderr}")
            self.mark_failed(track, e)
            return False
        except Exception as e:
            print(f"\n❌ Error: {e}")
            self.mark_failed(track, e)
            return False
    
    def run(self, max_tracks_per_run=2):
        tracks_processed = 0
        
        while tracks_processed < max_tracks_per_run:
            track = self.get_next_track()
            
            if track is None:
                print("\n✅ All tracks processed!")
                self.progress['status'] = 'completed'
                self.save_progress()
                break
            
            success = self.generate_track(track)
            tracks_processed += 1
            
            if tracks_processed >= max_tracks_per_run and not self.is_complete():
                print(f"\n⏸️  Processed {tracks_processed} tracks. Pausing...")
                self.progress['status'] = 'paused'
                self.save_progress()
                return False
        
        if self.is_complete():
            print("\n🎉 Album generation complete!")
            self.progress['status'] = 'completed'
            self.save_progress()
            return True
        
        return False

if __name__ == "__main__":
    if len(sys.argv) < 2:
        print("Usage: python album_pipeline.py <album_json_file>")
        sys.exit(1)
    
    album_json = sys.argv[1]
    max_tracks = int(sys.argv[2]) if len(sys.argv) > 2 else 2
    
    if not os.path.exists(album_json):
        print(f"❌ Album file not found: {album_json}")
        sys.exit(1)
    
    pipeline = AlbumPipeline(album_json)
    completed = pipeline.run(max_tracks_per_run=max_tracks)
    
    print("\n" + "="*60)
    print(f"📊 Progress Summary")
    print("="*60)
    print(f"Album: {pipeline.progress['album']}")
    print(f"Artist: {pipeline.progress['artist']}")
    print(f"Completed: {len(pipeline.progress['completed_tracks'])}/{pipeline.progress['total_tracks']}")
    print(f"Failed: {len(pipeline.progress['failed_tracks'])}")
    print(f"Status: {pipeline.progress['status']}")
    print("="*60)
    
    sys.exit(0 if completed else 2)