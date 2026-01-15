import json
import os
from moviepy import VideoFileClip, concatenate_videoclips

def merge_album_videos(progress_file='album_progress.json', output_dir='outputs'):
    with open(progress_file, 'r') as f:
        progress = json.load(f)
    
    if not progress['completed_tracks']:
        print("❌ No completed tracks to merge")
        return
    
    print(f"🎬 Merging {len(progress['completed_tracks'])} videos...")
    
    clips = []
    for track_info in sorted(progress['completed_tracks'], key=lambda x: int(x['position'])):
        video_path = track_info['video_path']
        
        if os.path.exists(video_path):
            print(f"  ✓ Loading track {track_info['position']}: {track_info['title']}")
            clip = VideoFileClip(video_path)
            clips.append(clip)
        else:
            print(f"  ✗ Missing: {video_path}")
    
    if not clips:
        print("❌ No valid video files found")
        return
    
    print(f"\n🔗 Concatenating {len(clips)} videos...")
    final_video = concatenate_videoclips(clips, method="compose")
    
    album_name = progress['album'].replace(' ', '_').replace('/', '-')
    artist_name = progress['artist'].replace(' ', '_').replace('/', '-')
    output_path = os.path.join(output_dir, f'{artist_name}_{album_name}_full_album.mp4')
    
    print(f"💾 Rendering final album video...")
    final_video.write_videofile(
        output_path,
        fps=24,
        codec='libx264',
        audio_codec='aac',
        logger=None
    )
    
    total_duration = sum(c.duration for c in clips)
    
    print("\n" + "="*60)
    print("✅ FULL ALBUM VIDEO CREATED!")
    print("="*60)
    print(f"📁 Output: {output_path}")
    print(f"🎵 Album: {progress['album']}")
    print(f"🎤 Artist: {progress['artist']}")
    print(f"📊 Tracks: {len(clips)}")
    print(f"⏱️  Duration: {total_duration/60:.1f} minutes")
    print("="*60)
    
    final_video.close()
    for clip in clips:
        clip.close()

if __name__ == "__main__":
    merge_album_videos()