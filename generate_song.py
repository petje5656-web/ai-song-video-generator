import os
import sys
from gradio_client import Client
import shutil
import soundfile as sf
from pydub import AudioSegment
from pydub.playback import play

print("=" * 60)
print("🎵 SONG GENERATION STARTING")
print("=" * 60)

if not os.path.exists("structured_lyrics.txt"):
    print("❌ Error: structured_lyrics.txt not found!")
    print("Run fetch_lyrics.py first to generate lyrics.")
    sys.exit(1)

with open("structured_lyrics.txt", 'r', encoding='utf-8') as f:
    lyrics = f.read()

if not lyrics.strip():
    print("❌ Error: structured_lyrics.txt is empty!")
    sys.exit(1)

title = "Hey Jude"
artist = "The Beatles"

print(f"\n🎤 Song: '{title}' by {artist}")
print("🎧 Style: Lofi pop, slowed reverb")
print("⏳ Connecting to AI music generator...\n")

try:
    client = Client("tencent/SongGeneration")
    print("✓ Connected to Gradio API\n")
except Exception as e:
    print(f"❌ Error connecting to API: {e}")
    sys.exit(1)

print("⏳ Generating song (this may take 2-5 minutes)...\n")

try:
    result = client.predict(
        lyric=lyrics,
        description=f"Female, dark, jazz, piano, guitar and drums, the bpm is 85, Lofi, chill beats, mellow, dreamy, 1950s",
        prompt_audio=None,
        genre="Auto",
        cfg_coef=1.5,
        temperature=0.8,
        api_name="/generate_song"
    )
    print(result) 
except Exception as e:
    print(f"❌ Error generating song: {e}")
    sys.exit(1)

if isinstance(result, (list, tuple)) and len(result) >= 2:
    audio_path = result[0]
    metadata = result[1] if isinstance(result[1], dict) else {}
else:
    audio_path = result if isinstance(result, str) else result[0]
    metadata = {}

print("=" * 60)
print("✅ SONG GENERATED SUCCESSFULLY!")
print("=" * 60)
print(f"📁 Original file: {audio_path}")
if metadata and 'inference_duration' in metadata:
    print(f"⏱️  Generation time: {metadata['inference_duration']:.1f}s")
else:
    print(f"⏱️  Generation complete")

output_filename = f"{title.replace(' ', '_').lower()}_ai_cover.flac"
slowed_filename = f"{title.replace(' ', '_').lower()}_ai_cover_slowed.flac"

print("\n🎛️  Slowing audio to 0.8x speed for lofi effect...")

try:
    audio = AudioSegment.from_file(audio_path)
    slowed_audio = audio._spawn(audio.raw_data, overrides={
        "frame_rate": int(audio.frame_rate * 0.8)
    })
    slowed_audio = slowed_audio.set_frame_rate(audio.frame_rate)
    
    slowed_audio.export(slowed_filename, format="flac")
    shutil.copy(audio_path, output_filename)
except Exception as e:
    print(f"❌ Error processing audio: {e}")
    sys.exit(1)

print("=" * 60)
print("✅ AUDIO PROCESSING COMPLETE!")
print("=" * 60)
print(f"📁 Original (1.0x): {output_filename}")
print(f"📁 Slowed (0.8x): {slowed_filename}")
print(f"🎵 Duration: {len(slowed_audio) / 1000:.2f}s")
print("=" * 60)

print("\n🔊 Attempting playback (may not work in CI environment)...")
try:
    play(slowed_audio)
except:
    print("⚠️  Playback not available in this environment (expected in CI)")

print("\n✅ Files saved! Run create_video.py next to make the music video.")
