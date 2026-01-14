from gradio_client import Client
import shutil
import soundfile as sf
from pydub import AudioSegment
from pydub.playback import play
import os

print("=" * 60)
print("🎵 SONG GENERATION STARTING")
print("=" * 60)

client = Client("tencent/SongGeneration")

with open("structured_lyrics.txt", 'r', encoding='utf-8') as f:
    lyrics = f.read()

title = "Hey Jude"
artist = "The Beatles"

print(f"\n🎤 Song: '{title}' by {artist}")
print("🎧 Style: Lofi pop, slowed reverb")
print("⏳ Generating song (this may take 2-5 minutes)...\n")

result = client.predict(
    lyric=lyrics,
    description=f"Lofi pop, chill beats, mellow, dreamy, inspired by {title}",
    prompt_audio=None,
    genre="Auto",
    cfg_coef=1.5,
    temperature=0.8,
    api_name="/generate_song"
)

audio_path, metadata = result

print("=" * 60)
print("✅ SONG GENERATED SUCCESSFULLY!")
print("=" * 60)
print(f"📁 Original file: {audio_path}")
print(f"⏱️  Generation time: {metadata['inference_duration']:.1f}s")

output_filename = f"{title.replace(' ', '_').lower()}_ai_cover.flac"
slowed_filename = f"{title.replace(' ', '_').lower()}_ai_cover_slowed.flac"

print("\n🎛️  Slowing audio to 0.8x speed for lofi effect...")

audio = AudioSegment.from_file(audio_path)
slowed_audio = audio._spawn(audio.raw_data, overrides={
    "frame_rate": int(audio.frame_rate * 0.8)
})
slowed_audio = slowed_audio.set_frame_rate(audio.frame_rate)

slowed_audio.export(slowed_filename, format="flac")

shutil.copy(audio_path, output_filename)

print("=" * 60)
print("✅ AUDIO PROCESSING COMPLETE!")
print("=" * 60)
print(f"📁 Original (1.0x): {output_filename}")
print(f"📁 Slowed (0.8x): {slowed_filename}")
print(f"🎵 Duration: {len(slowed_audio) / 1000:.2f}s")
print("=" * 60)

print("\n🔊 Playing slowed version (0.8x)...")
try:
    play(slowed_audio)
except:
    print("⚠️  Playback not available in this environment")

print("\n✅ Files saved! Run create_video.py next to make the music video.")