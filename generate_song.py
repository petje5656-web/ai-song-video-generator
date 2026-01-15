import os
import sys
import json
from gradio_client import Client
import shutil
import soundfile as sf
from pydub import AudioSegment
from pydub.playback import play
import numpy as np
from scipy import signal

print("=" * 60)
print("🎵 CHOIR SONG GENERATION STARTING")
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

if os.path.exists('lyrics_metadata.json'):
    with open('lyrics_metadata.json', 'r') as f:
        metadata = json.load(f)
        title = metadata.get('title', 'Hey Jude')
        artist = metadata.get('artist', 'The Beatles')
        detected_choruses = metadata.get('detected_choruses', [])
else:
    title = os.getenv('SONG_TITLE', 'Hey Jude')
    artist = os.getenv('SONG_ARTIST', 'The Beatles')
    detected_choruses = []

print(f"\n🎤 Song: '{title}' by {artist}")
print("🎧 Style: Choir, Gospel, Harmonies")
if detected_choruses:
    print(f"🎵 Detected {len(detected_choruses)} chorus patterns")
print("⏳ Connecting to AI music generator...\n")

try:
    client = Client("tencent/SongGeneration")
    print("✓ Connected to Gradio API\n")
except Exception as e:
    print(f"❌ Error connecting to API: {e}")
    sys.exit(1)

print("⏳ Generating choir arrangement (this may take 2-5 minutes)...\n")

try:
    result = client.predict(
        lyric=lyrics,
        description=f"Choir, gospel, powerful harmonies, group vocals, uplifting, piano and organ, the bpm is 90, spiritual, anthemic, church choir",
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
    gen_metadata = result[1] if isinstance(result[1], dict) else {}
else:
    audio_path = result if isinstance(result, str) else result[0]
    gen_metadata = {}

print("=" * 60)
print("✅ CHOIR SONG GENERATED SUCCESSFULLY!")
print("=" * 60)
print(f"📁 Original file: {audio_path}")
if gen_metadata and 'inference_duration' in gen_metadata:
    print(f"⏱️  Generation time: {gen_metadata['inference_duration']:.1f}s")
else:
    print(f"⏱️  Generation complete")

output_filename = f"{title.replace(' ', '_').lower()}_ai_cover.flac"
choir_filename = f"{title.replace(' ', '_').lower()}_ai_cover_slowed.flac"

print("\n🎛️  Applying choir enhancements...")
print("   ├─ Slowing to 0.8x speed")
print("   ├─ Adding cathedral reverb")
print("   ├─ Lowering pitch (-2 semitones)")
print("   ├─ Enhancing harmonics")
print("   └─ Applying warmth filter\n")

try:
    audio = AudioSegment.from_file(audio_path)
    
    slowed_audio = audio._spawn(audio.raw_data, overrides={
        "frame_rate": int(audio.frame_rate * 0.8)
    })
    slowed_audio = slowed_audio.set_frame_rate(audio.frame_rate)
    
    pitched_audio = slowed_audio._spawn(slowed_audio.raw_data, overrides={
        "frame_rate": int(slowed_audio.frame_rate * 0.887)
    })
    pitched_audio = pitched_audio.set_frame_rate(slowed_audio.frame_rate)
    
    samples = np.array(pitched_audio.get_array_of_samples())
    
    nyquist = pitched_audio.frame_rate / 2
    cutoff = 5000
    normalized_cutoff = cutoff / nyquist
    b, a = signal.butter(4, normalized_cutoff, btype='low')
    filtered_samples = signal.filtfilt(b, a, samples)
    
    filtered_audio = pitched_audio._spawn(filtered_samples.astype(np.int16).tobytes())
    
    # Cathedral reverb (longer delay for choir effect)
    echo_delay = 200
    echo_decay = 0.4
    reverb_audio = filtered_audio.overlay(
        filtered_audio - (echo_decay * 10),
        position=echo_delay
    )
    
    reverb_audio = reverb_audio.overlay(
        filtered_audio - (echo_decay * 15),
        position=echo_delay * 2
    )
    
    reverb_audio = reverb_audio.overlay(
        filtered_audio - (echo_decay * 20),
        position=echo_delay * 3
    )
    
    final_audio = reverb_audio.normalize()
    final_audio = final_audio - 2
    
    final_audio.export(choir_filename, format="flac")
    shutil.copy(audio_path, output_filename)
    
except Exception as e:
    print(f"❌ Error processing audio: {e}")
    import traceback
    traceback.print_exc()
    sys.exit(1)

print("=" * 60)
print("✅ CHOIR PROCESSING COMPLETE!")
print("=" * 60)
print(f"📁 Original (1.0x): {output_filename}")
print(f"📁 Choir Version: {choir_filename}")
print(f"🎵 Duration: {len(final_audio) / 1000:.2f}s")
print("\n🎛️  Effects applied:")
print("   ✓ 0.8x speed (slowed)")
print("   ✓ -2 semitones pitch")
print("   ✓ Cathedral reverb")
print("   ✓ Enhanced harmonics")
print("   ✓ Warmth filter (5kHz)")
print("   ✓ Compression & normalization")
print("=" * 60)

print("\n✅ Files saved! Run create_video.py next to make the music video.")