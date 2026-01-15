import os
import json
import random
import zipfile
import soundfile as sf
import numpy as np
from moviepy import VideoFileClip, AudioFileClip, concatenate_videoclips

ZIP_PATH = 'data/giphy.zip'
EXTRACT_DIR = 'gifs_extracted'
OUTPUT_DIR = 'outputs'

os.makedirs(EXTRACT_DIR, exist_ok=True)
os.makedirs(OUTPUT_DIR, exist_ok=True)

print("📦 Extracting GIFs...")
with zipfile.ZipFile(ZIP_PATH, 'r') as zip_ref:
    zip_ref.extractall(EXTRACT_DIR)

gif_files = [f for f in os.listdir(EXTRACT_DIR) if f.lower().endswith('.gif')]
print(f"✓ Found {len(gif_files)} GIFs\n")

# FIXED: Read metadata from lyrics_metadata.json if available
if os.path.exists('lyrics_metadata.json'):
    with open('lyrics_metadata.json', 'r') as f:
        metadata = json.load(f)
        title = metadata.get('title', 'Hey Jude')
        artist = metadata.get('artist', 'The Beatles')
else:
    # Fallback to environment variables or defaults
    title = os.getenv('SONG_TITLE', 'Hey Jude')
    artist = os.getenv('SONG_ARTIST', 'The Beatles')

song_filename = f"{title.replace(' ', '_').lower()}_ai_cover_slowed.flac"

if not os.path.exists(song_filename):
    print(f"❌ Error: Audio file '{song_filename}' not found!")
    print("Run generate_song.py first to create the audio file.")
    exit(1)

print("🎵 Converting song to WAV...")
audio_data, sample_rate = sf.read(song_filename)
wav_path = os.path.join(OUTPUT_DIR, 'song.wav')
sf.write(wav_path, audio_data, sample_rate)

audio_clip = AudioFileClip(wav_path)
audio_duration = audio_clip.duration
print(f"✓ Song duration: {audio_duration:.2f}s\n")

TARGET_WIDTH = 2080
TARGET_HEIGHT = 1920

def load_and_process_gif(gif_path):
    """Load and resize a single GIF"""
    try:
        clip = VideoFileClip(gif_path)
        
        clip_aspect = clip.w / clip.h
        target_aspect = TARGET_WIDTH / TARGET_HEIGHT
        
        if clip_aspect > target_aspect:
            new_height = TARGET_HEIGHT
            new_width = int(clip.w * (TARGET_HEIGHT / clip.h))
            clip = clip.resized(height=new_height)
            x_center = (new_width - TARGET_WIDTH) // 2
            clip = clip.cropped(x1=x_center, width=TARGET_WIDTH)
        else:
            new_width = TARGET_WIDTH
            new_height = int(clip.h * (TARGET_WIDTH / clip.w))
            clip = clip.resized(width=new_width)
            y_center = (new_height - TARGET_HEIGHT) // 2
            clip = clip.cropped(y1=y_center, height=TARGET_HEIGHT)
        
        return clip
    except Exception as e:
        print(f"  ⚠ Error loading {os.path.basename(gif_path)}: {e}")
        return None

def get_random_clips_no_repeat(gif_files, target_duration):
    """
    Get clips in random order without repeating until all are used.
    When exhausted, reshuffle and continue.
    """
    video_clips = []
    total_duration = 0
    available_gifs = gif_files.copy()
    random.shuffle(available_gifs)
    
    used_count = 0
    rounds = 0
    
    print(f"🎬 Loading GIFs randomly (target: {target_duration:.2f}s)...\n")
    
    while total_duration < target_duration:
        if not available_gifs:
            rounds += 1
            print(f"🔄 Round {rounds} complete, reshuffling...\n")
            available_gifs = gif_files.copy()
            random.shuffle(available_gifs)
        
        gif_file = available_gifs.pop(0)
        gif_path = os.path.join(EXTRACT_DIR, gif_file)
        
        clip = load_and_process_gif(gif_path)
        if clip:
            video_clips.append(clip)
            total_duration += clip.duration
            used_count += 1
            
            if used_count % 5 == 0:
                print(f"  Loaded {used_count} GIFs (duration: {total_duration:.2f}s / {target_duration:.2f}s)")
    
    print(f"\n✓ Loaded {len(video_clips)} GIFs (total: {total_duration:.2f}s)")
    print(f"✓ Went through {rounds + 1} round(s) of the GIF collection\n")
    
    return video_clips

video_clips = get_random_clips_no_repeat(gif_files, audio_duration)

if len(video_clips) == 0:
    print("❌ No GIFs loaded successfully!")
    exit(1)

print("🎞️ Combining clips and adding music...")
full_sequence = concatenate_videoclips(video_clips, method="compose")
final_video = full_sequence.subclipped(0, audio_duration)
final_video = final_video.with_audio(audio_clip)

# FIXED: Use consistent filename format that album_pipeline.py expects
output_filename = f'{title.replace(" ", "_").lower()}_lofi_music_video.mp4'
output_path = os.path.join(OUTPUT_DIR, output_filename)
print(f"💾 Rendering final video to: {output_path}\n")

final_video.write_videofile(
    output_path, 
    fps=24, 
    codec='libx264', 
    audio_codec='aac',
    logger=None
)

# FIXED: Verify file was created
if not os.path.exists(output_path):
    print(f"❌ ERROR: Video file was not created at {output_path}")
    exit(1)

file_size = os.path.getsize(output_path) / (1024 * 1024)  # MB

print("=" * 60)
print("✅ MUSIC VIDEO CREATED!")
print("=" * 60)
print(f"📁 Output: {output_path}")
print(f"📦 Size: {file_size:.2f} MB")
print(f"🎵 Song: '{title}' by {artist} (Lofi 0.8x)")
print(f"⏱️  Duration: {audio_duration:.2f}s")
print(f"🎬 GIFs used: {len(video_clips)}")
print("=" * 60)

audio_clip.close()
final_video.close()
for clip in video_clips:
    clip.close()

print("\n✓ Done!")
